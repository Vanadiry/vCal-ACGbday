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
    for i, p in enumerate(files):
        d = yaml.safe_load(p.read_text(encoding="utf-8"))
        refs = d.get("refs") or {}
        bday = d.get("bday") or {}
        work = p.parent.name
        cn = p.stem

        srcs = {}  # 'month'/'day'/'year' -> [(src, value)]
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
                        counts["source_unavailable"] += 1
                        continue
                    for k in ("month", "day", "year"):
                        v = res["birth"][k]
                        if v is not None:
                            srcs.setdefault(k, []).append((sname, v))

        # 月/日分开判定（yml 键 m/d ↔ 逻辑键 month/day）
        entry = {"work": work, "character": cn, "sources": {}}
        issues = []
        local_map = {"month": bday.get("m"), "day": bday.get("d"), "year": bday.get("y")}
        for k in ("month", "day"):
            status, note = judge(srcs.get(k, []), local_map[k])
            counts[status] += 1
            if status == "pass":
                continue
            entry["sources"][k] = {"local": local_map[k], "status": status, "note": note}
            issues.append(k)

        # 年份：判定 + 补全
        y_status, y_note = judge(srcs.get("year", []), local_map["year"])
        if y_status == "patch":
            assert isinstance(y_note, tuple) and len(y_note) == 2
            src_name, val = y_note
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
                entry["sources"]["year"] = {
                    "local": None,
                    "patched": val,
                    "status": "patched",
                    "note": f"补全年份 from {src_name}",
                }
                issues.append("year")
            else:
                counts[y_status] += 1
                if y_status != "pass":
                    entry["sources"]["year"] = {
                        "local": local_map["year"],
                        "status": y_status,
                        "note": y_note,
                    }
                    issues.append("year")
        elif y_status != "pass":
            counts[y_status] += 1
            entry["sources"]["year"] = {
                "local": local_map["year"],
                "status": y_status,
                "note": y_note,
            }
            issues.append("year")
        else:
            counts["pass"] += 1

        if issues:
            items.append(entry)
        print(
            f"  [{i + 1}/{len(files)}] {work}/{cn}: {','.join(issues) if issues else 'PASS'}",
            flush=True,
        )

    # 汇总
    print("\n== 汇总 ==")
    for k, v in counts.items():
        print(f"  {k}: {v}")

    report = {
        "generated": datetime.now().isoformat(timespec="seconds"),
        "summary": dict(counts),
        "items": items,
    }
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        yaml.safe_dump(report, allow_unicode=True, sort_keys=False, default_flow_style=False),
        encoding="utf-8",
    )
    print(f"\n报告已写入: {report_path}")


if __name__ == "__main__":
    main()
