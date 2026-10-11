# 检查 dist 下的 ICS 文件合法性（用 icalendar 解析）

import argparse
import re
import sys
from datetime import date
from pathlib import Path

from icalendar import Calendar

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.lib.color import bold, error, ok, warn


# TEXT 值中未转义的字符（RFC 5545 §3.3.11）。合法转义序列为
# \\ 、\; 、\, 、\N 或 \n，即反斜杠后跟这些字符时不算未转义。
def find_unescaped(value):
    """返回 value 中未转义的字符列表。逐字符扫描以正确处理 \\ 成对的情况。"""
    bad = []
    i = 0
    while i < len(value):
        c = value[i]
        if c == "\\":
            nxt = value[i + 1] if i + 1 < len(value) else ""
            if nxt in ("\\", ";", ",", "N", "n"):
                i += 2
                continue
            bad.append(c)
            i += 1
        elif c in ",;":
            bad.append(c)
            i += 1
        else:
            i += 1
    return bad


TEXT_PROPS = ("SUMMARY", "DESCRIPTION", "LOCATION", "CATEGORIES")
DTSTAMP_RE = re.compile(r"^DTSTAMP(?:;VALUE=DATE)?:(\d{8})(?:T\d{6}Z)?$")


def check_lines(text):
    """逐行检查内容行规范（RFC 5545 §3.1 / §3.3.11）。"""
    problems = []
    for lineno, line in enumerate(text.split("\n"), 1):
        if not line:
            continue
        name = re.match(r"^([A-Z-]+)(;[^:]*)?:(.*)$", line)
        if not name:
            problems.append(f"第 {lineno} 行无法解析: {line[:40]}")
            continue
        prop, value = name.group(1), name.group(3)
        # 内容行不得超过 75 octet（§3.1），续行以空格开头，不单独检查
        width = len(line.encode("utf-8"))
        if width > 75:
            problems.append(f"第 {lineno} 行超长 {width} octet（上限 75）: {prop}")
        if prop in TEXT_PROPS:
            bad = find_unescaped(value)
            if bad:
                problems.append(f"第 {lineno} 行 {prop} 含未转义字符 {bad}")
    return problems


def check_uids(events):
    """同一文件内 UID 必须唯一，重复会让客户端只保留其中一条。"""
    seen = {}
    problems = []
    for ev in events:
        uid = ev.get("UID")
        if uid is None:
            continue
        uid = str(uid)
        if uid in seen:
            problems.append(f"UID 重复: {uid}（与第 {seen[uid]} 条）")
        else:
            seen[uid] = len(seen) + 1
    return problems


def check_dates(path):
    """DTSTART 须为真实存在的日历日期，如 2 月 30 日应报错。"""
    problems = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").split("\n"), 1):
        m = re.match(r"^DTSTART(?:;VALUE=DATE)?:(\d{4})(\d{2})(\d{2})", line)
        if not m:
            continue
        year, month, day = (int(g) for g in m.groups())
        try:
            date(year, month, day)
        except ValueError as e:
            problems.append(f"第 {lineno} 行 DTSTART 日期不存在: {year}{month:02d}{day:02d} ({e})")
    return problems


def check_ics(path):
    problems = []
    with open(path, "rb") as f:
        data = f.read()
    try:
        cal = Calendar.from_ical(data)
    except Exception as e:
        return [f"解析失败: {e}"]

    text = data.decode("utf-8")
    problems += check_lines(text)

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
    problems += check_uids(events)
    problems += check_dates(path)
    return problems


def main():
    parser = argparse.ArgumentParser(description="检查 dist 下 ICS 合法性")
    parser.add_argument("--dist", default="dist", help="dist 目录")
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
