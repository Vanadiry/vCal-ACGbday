# 生日数据全面检查。比较 data 与 bgm API / 萌娘百科，补全缺失年份。
# 月日与年份分开检查，各自套用同一套规则。

import argparse
import os
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import bangumi, moegirl
from lib.status import status_mark


class BlockDumper(yaml.SafeDumper):
    pass


def str_rep(dumper, data):
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


# 判定


def judge_field(src_values, local_value):
    """单个字段（month/day/year）判定。
    src_values: 有效源（有数据）列表 [(src, value)]。
    返回 (code, note)。code: Y/X/?/patch"""
    if not src_values:
        # 无有效源
        if local_value is None:
            return "none", None  # data 也没有，lint 管
        return "need_src", None  # data 有但源缺失，需补源
    if len(src_values) == 1:
        src, val = src_values[0]
        if local_value is not None and val == local_value:
            return "Y", None
        if local_value is None:
            return "patch", (src, val)  # 单源可补
        return "X", f"{src}:{val} != data:{local_value}"
    # 两源
    v0, v1 = src_values[0][1], src_values[1][1]
    s0, s1 = src_values[0][0], src_values[1][0]
    if v0 == v1:
        if local_value is not None and v0 == local_value:
            return "Y", None
        if local_value is None:
            return "patch", (s0, v0)  # 两源相同可补
        return "X", f"{s0}/{s1}:{v0} != data:{local_value}"
    # 两源不同
    if local_value is not None and local_value == v0:
        return "?", f"{s1}:{v1} 与 data 不同，源 {s1} 可能有问题"
    if local_value is not None and local_value == v1:
        return "?", f"{s0}:{v0} 与 data 不同，源 {s0} 可能有问题"
    if local_value is None:
        # 两源不同 + data 缺该字段：year 需要看日月是否一致，此处返回特殊标记
        return "patch_conflict", f"{s0}:{v0} vs {s1}:{v1}"
    return "X", f"{s0}:{v0} vs {s1}:{v1} vs data:{local_value}"


# 主流程


def process_one(p, idx, total):
    """处理单个角色。返回 (entry, issues, line)。"""
    d = yaml.safe_load(p.read_text(encoding="utf-8"))
    refs = d.get("refs") or {}
    bday = d.get("bday") or {}
    work = p.parent.name
    cn = p.stem

    # verified: 已通过其他途径确认，跳过联网检查
    if bday.get("verified") is True:
        counts = Counter()
        entry = {"work": work, "character": cn, "sources": {}, "verified": True}
        name_col = f"{work}/{cn}"
        line = f"  [{idx + 1}/{total}] {status_mark('Y')} {name_col} [verified]"
        return entry, [], line, counts

    srcs = {}  # 'month'/'day'/'year' -> [(src, value)]
    unavailable = []  # [(src, detail)] 源不可用
    tasks = []
    for sname, getter in (("bangumi", bangumi.fetch), ("moegirl", moegirl.fetch)):
        sid = refs.get("bangumi") if sname == "bangumi" else refs.get("moegirl")
        if sid is None:
            continue
        key = int(sid) if sname == "bangumi" else sid
        tasks.append((sname, getter, key))

    if tasks:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = pool.map(lambda t: (t[0], t[1](t[2])), tasks)
            for sname, res in results:
                if not res["found"] or res["birth"] is None:
                    unavailable.append((sname, res.get("detail") or "无生日数据"))
                    continue
                for k in ("month", "day", "year"):
                    v = res["birth"][k]
                    if v is not None:
                        srcs.setdefault(k, []).append((sname, v))

    entry = {"work": work, "character": cn, "sources": {}}
    issues = []
    counts = Counter()
    local_map = {"month": bday.get("m"), "day": bday.get("d"), "year": bday.get("y")}

    # 区分 404 与无数据，收集提示
    nodata_hints = []  # 非 404 的缺失源
    gone_404 = []  # 404 的源
    for sname, detail in unavailable:
        if "404" in (detail or ""):
            gone_404.append(sname)
        else:
            nodata_hints.append(sname)
    if unavailable:
        entry["unavailable"] = [{"source": s, "detail": d} for s, d in unavailable]

    # 月/日判定
    for k in ("month", "day"):
        code, note = judge_field(srcs.get(k, []), local_map[k])
        if code == "Y":
            counts["Y"] += 1
            continue
        if code == "none":
            counts["none"] += 1
            continue  # data 也缺，lint 管
        counts["X"] += 1
        entry["sources"][k] = {
            "local": local_map[k],
            "status": code,
            "note": note or "所有数据源均无此字段，需补充数据源",
        }
        if code == "need_src":
            issues.append((k, "X", "缺源"))
        elif code == "?":
            issues.append((k, "?", ""))
        else:
            issues.append((k, "X", ""))

    # 年份判定
    y_code, y_note = judge_field(srcs.get("year", []), local_map["year"])
    if y_code == "Y":
        counts["Y"] += 1
    elif y_code == "none":
        counts["none"] += 1
    elif y_code == "patch":
        # 允许自动补全
        src_name, val = y_note
        bday["y"] = val
        d["bday"] = bday
        p.write_text(
            yaml.dump(
                d,
                Dumper=BlockDumper,
                allow_unicode=True,
                sort_keys=False,
                default_flow_style=False,
            ),
            encoding="utf-8",
        )
        counts["patched_year"] += 1
        entry["sources"]["year"] = {
            "local": None,
            "patched": val,
            "status": "patched",
            "note": f"补全年份 {val} from {src_name}",
        }
        issues.append(("year", "?", f"源({src_name})"))
    elif y_code == "patch_conflict":
        # 两源不同且 data 缺年：若日月一致且仅一源有年，可补全；否则不补
        year_srcs = srcs.get("year", [])
        month_srcs = srcs.get("month", [])
        day_srcs = srcs.get("day", [])
        # 日月是否一致（有值的源）
        month_vals = {v for _, v in month_srcs}
        day_vals = {v for _, v in day_srcs}
        if (
            len(month_vals) == 1
            and len(day_vals) == 1
            and local_map["month"] in month_vals
            and local_map["day"] in day_vals
        ):
            # 一源有年一源缺年
            has_year = [s for s, v in year_srcs if v is not None]
            if len(has_year) == 1:
                src_name = has_year[0]
                val = [v for s, v in year_srcs if s == src_name][0]
                bday["y"] = val
                d["bday"] = bday
                p.write_text(
                    yaml.dump(
                        d,
                        Dumper=BlockDumper,
                        allow_unicode=True,
                        sort_keys=False,
                        default_flow_style=False,
                    ),
                    encoding="utf-8",
                )
                counts["patched_year"] += 1
                entry["sources"]["year"] = {
                    "local": None,
                    "patched": val,
                    "status": "patched",
                    "note": f"补全年份 {val} from {src_name}",
                }
                issues.append(("year", "?", f"源({src_name})"))
            else:
                counts["X"] += 1
                entry["sources"]["year"] = {
                    "local": None,
                    "status": "X",
                    "note": f"两源年份不同: {y_note}",
                }
                issues.append(("year", "?", ""))
        else:
            counts["X"] += 1
            entry["sources"]["year"] = {
                "local": local_map["year"],
                "status": "X",
                "note": f"两源年份不同: {y_note}",
            }
            issues.append(("year", "?", ""))
    elif y_code == "need_src":
        counts["X"] += 1
        entry["sources"]["year"] = {
            "local": local_map["year"],
            "status": "need_src",
            "note": "所有数据源均无此字段，需补充数据源",
        }
        issues.append(("year", "X", "缺源"))
    elif y_code == "?":
        counts["?"] += 1
        entry["sources"]["year"] = {
            "local": local_map["year"],
            "status": "?",
            "note": y_note,
        }
        issues.append(("year", "?", ""))
    else:  # X
        counts["X"] += 1
        entry["sources"]["year"] = {
            "local": local_map["year"],
            "status": "X",
            "note": y_note,
        }
        issues.append(("year", "X", ""))

    # 404 提示
    if gone_404:
        for sname in gone_404:
            issues.append((f"refs:{sname}", "X", "404应删除该源"))

    # 输出
    name_col = f"{work}/{cn}"
    if not issues:
        code = "Y"
        detail = ""
        if nodata_hints:
            detail = " [" + ", ".join(f"refs:{s}:nodata" for s in nodata_hints) + "]"
        if gone_404:
            detail += " [" + ", ".join(f"refs:{s}:404" for s in gone_404) + "]"
    else:
        codes = {c for _, c, _ in issues}
        code = "?" if "?" in codes else "X"
        parts = []
        for key, _c, src_desc in issues:
            parts.append(f"{key}{'+' + src_desc if src_desc else ''}")
        detail = " " + ", ".join(parts)
    line = f"  [{idx + 1}/{total}] {status_mark(code)} {name_col}{detail}"
    return entry, issues, line, counts


def main():
    BlockDumper.add_representer(str, str_rep)

    parser = argparse.ArgumentParser(description="生日数据全面检查")
    parser.add_argument("--data", default="data", help="数据目录（默认 data）")
    parser.add_argument("--report", default="report/bday_report.yml", help="报告输出路径")
    parser.add_argument("--no-color", action="store_true", help="关闭彩色输出")
    args = parser.parse_args()

    if args.no_color:
        os.environ["NO_COLOR"] = "1"

    data_dir = Path(args.data)
    if not data_dir.is_dir():
        print(f"数据目录不存在: {data_dir}")
        sys.exit(2)

    files = [p for p in data_dir.rglob("*.yml") if p.is_file() and p.name != "_info.yaml"]
    print(f"扫描: {len(files)} 个角色", flush=True)

    # 前置 lint 检查，不通过则终止
    from lint import run_lint

    lint_errs = run_lint(data_dir, str(Path(args.report).with_suffix(".lint.yml")))
    if lint_errs != 0:
        print("\nlint 检查未通过，请先修正数据再运行 vc-bday")
        sys.exit(1)

    items = []
    counts = Counter()
    total = len(files)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = pool.map(process_one, files, range(total), [total] * total)
        for i, (entry, issues, line, c) in enumerate(results):
            counts.update(c)
            if issues:
                items.append(entry)
            print(line, flush=True)
            write_report(args.report, files, items, counts, i + 1)

    # 汇总
    print("\n== 汇总 ==")
    for k, v in counts.items():
        print(f"  {k}: {v}")
    write_report(args.report, files, items, counts, total)
    print(f"\n报告已写入: {args.report}")


def write_report(report_path, files, items, counts, processed):
    report = {
        "generated": datetime.now().isoformat(timespec="seconds"),
        "summary": {
            "total": len(files),
            "processed": processed,
            **dict(counts),
        },
        "items": items,
    }
    p = Path(report_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        yaml.safe_dump(report, allow_unicode=True, sort_keys=False, default_flow_style=False),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
