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
from lib import bangumi, moegirl
from lib.status import status_mark


class BlockDumper(yaml.SafeDumper):
    pass


def str_rep(dumper, data):
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


# 判定


def judge(
    src_values: list[tuple[str, int]], local_value: int | None
) -> tuple[str, str | tuple[str, int] | None]:
    # 5条规则判定，返回 (status, note)。patch 时 note 为 (src, value) 元组
    if not src_values:
        return "pass", None
    if len(src_values) == 1:
        src, val = src_values[0]
        if local_value is not None and val == local_value:
            return "pass", None
        if local_value is None:
            return "patch", (src, val)  # 缺值，单源可补
        return "yellow", f"{src}:{val} != data:{local_value}"
    # 两源
    v0, v1 = src_values[0][1], src_values[1][1]
    s0, s1 = src_values[0][0], src_values[1][0]
    if v0 == v1:
        if local_value is not None and v0 == local_value:
            return "pass", None
        if local_value is None:
            return "patch", (s0, v0)  # 缺值，两源相同可补
        return "yellow", f"{s0}/{s1}:{v0} != data:{local_value}"
    # 两源不同
    if local_value is not None and local_value != v0 and local_value != v1:
        return "red", f"{s0}:{v0} vs {s1}:{v1} vs data:{local_value}"
    return "yellow", f"{s0}:{v0} vs {s1}:{v1}"


# 主流程


def process_one(p, idx, total):
    """处理单个角色。返回 (entry, issues, line)。"""
    d = yaml.safe_load(p.read_text(encoding="utf-8"))
    refs = d.get("refs") or {}
    bday = d.get("bday") or {}
    work = p.parent.name
    cn = p.stem

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

    if unavailable:
        entry["unavailable"] = [{"source": s, "detail": d} for s, d in unavailable]
        for sname, detail in unavailable:
            issues.append((f"src:{sname}", "?", detail))

    for k in ("month", "day"):
        status, note = judge(srcs.get(k, []), local_map[k])
        counts[status] += 1
        if status == "pass":
            continue
        entry["sources"][k] = {"local": local_map[k], "status": status, "note": note}
        issues.append((k, "X", ""))

    y_status, y_note = judge(srcs.get("year", []), local_map["year"])
    if y_status == "patch":
        assert isinstance(y_note, tuple) and len(y_note) == 2
        src_name, val = y_note
        year_srcs = [s for s, _ in srcs.get("year", [])]
        src_count = len(year_srcs)
        if local_map["year"] is None:
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
            src_desc = f"源({'/'.join(year_srcs)})" if src_count >= 2 else f"源({src_name})"
            entry["sources"]["year"] = {
                "local": None,
                "patched": val,
                "status": "patched",
                "note": f"补全年份 {val} from {src_desc}",
            }
            issues.append(("year", "?", src_desc))
        else:
            counts[y_status] += 1
            if y_status != "pass":
                entry["sources"]["year"] = {
                    "local": local_map["year"],
                    "status": y_status,
                    "note": y_note,
                }
                issues.append(("year", "X", ""))
    elif y_status != "pass":
        counts[y_status] += 1
        entry["sources"]["year"] = {
            "local": local_map["year"],
            "status": y_status,
            "note": y_note,
        }
        issues.append(("year", "X", ""))
    else:
        counts["pass"] += 1

    name_col = f"{work}/{cn}"
    if not issues:
        code = "Y"
        detail = ""
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
