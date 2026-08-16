# 检查 dist 下的 ICS 文件合法性（用 icalendar 解析）

import argparse
import sys
from pathlib import Path

from icalendar import Calendar

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.color import bold, error, ok, warn


def check_ics(path):
    problems = []
    with open(path, "rb") as f:
        data = f.read()
    try:
        cal = Calendar.from_ical(data)
    except Exception as e:
        return [f"解析失败: {e}"]

    events = [c for c in cal.walk() if c.name == "VEVENT"]
    if not events:
        problems.append("无 VEVENT")
    for ev in events:
        uid = ev.get("UID")
        if uid is None:
            problems.append("VEVENT 缺少 UID")
        summary = ev.get("SUMMARY")
        if summary is None:
            problems.append(f"UID={uid}: 缺少 SUMMARY")
        dtstart = ev.get("DTSTART")
        if dtstart is None:
            problems.append(f"UID={uid}: 缺少 DTSTART")
        dtstamp = ev.get("DTSTAMP")
        if dtstamp is None:
            problems.append(f"UID={uid}: 缺少 DTSTAMP")
    return problems


def main():
    parser = argparse.ArgumentParser(description="检查 dist 下 ICS 合法性")
    parser.add_argument("--dist", default="dist", help="dist 目录")
    parser.add_argument("--no-color", action="store_true")
    args = parser.parse_args()

    dist = Path(args.dist)
    if not dist.is_dir():
        print(error(f"目录不存在: {dist}"))
        sys.exit(2)

    ics_files = sorted(dist.glob("*.ics"))
    if not ics_files:
        print(warn("没有找到 .ics 文件"))
        sys.exit(0)

    total_problems = 0
    for p in ics_files:
        problems = check_ics(p)
        if problems:
            total_problems += len(problems)
            print(f"{error('E')} {p.name}")
            for pr in problems[:10]:
                print(f"    {pr}")
        else:
            print(f"{ok('OK')} {p.name}")

    print()
    print(bold("== 结果 =="))
    print(f"  文件: {len(ics_files)}, 问题: {total_problems}")
    sys.exit(1 if total_problems else 0)


if __name__ == "__main__":
    main()
