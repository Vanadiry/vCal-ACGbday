# 检查 dist 下的 ICS 文件合法性（用 icalendar 解析）

import argparse
import re
import sys
from datetime import date
from pathlib import Path

from icalendar import Calendar

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.lib.color import bold, error, ok, warn


# TEXT 值中未转义的字符（RFC 5545 §3.3.11）
# 合法转义序列为 \\ 、\; 、\, 、\N 或 \n，即反斜杠后跟这些字符时不算未转义
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
    """逐行检查内容行规范（RFC 5545 §3.1 / §3.3.11）。

    宽度按物理行判断（折行后每行都应 ≤75 octet）；属性名与 TEXT 转义
    按逻辑行判断，续行以空格开头，合并进所属逻辑行。
    """
    problems = []
    logical = None  # 当前逻辑行的 (起始行号, 内容)
    for lineno, physical in enumerate(text.split("\n"), 1):
        if not physical:
            continue
        # 宽度看物理行
        width = len(physical.encode("utf-8"))
        if width > 75:
            head = physical[:32] + ("…" if len(physical) > 32 else "")
            problems.append(f"第 {lineno} 行超长 {width} octet（上限 75）: {head}")
        if physical.startswith(" "):
            # 续行：并入上一逻辑行，去掉前导空格
            if logical is None:
                problems.append(f"第 {lineno} 行以空格开头，但无上一逻辑行")
                logical = (lineno, physical[1:])
            else:
                logical = (logical[0], logical[1] + physical[1:])
            continue
        if logical is not None:
            problems += check_logical(*logical)
        logical = (lineno, physical)
    if logical is not None:
        problems += check_logical(*logical)
    return problems


def check_logical(lineno, line):
    """检查一条逻辑行的属性名与 TEXT 转义。"""
    problems = []
    name = re.match(r"^([A-Z-]+)(;[^:]*)?:(.*)$", line)
    if not name:
        problems.append(f"第 {lineno} 行无法解析: {line[:40]}")
        return problems
    prop, value = name.group(1), name.group(3)
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


def classify(problem):
    """把问题归类，返回 (类别, 说明)。"""
    if "超长" in problem:
        return "行超长", "RFC 5545 §3.1，上限 75 octet"
    if "未转义" in problem:
        return "未转义", "RFC 5545 §3.3.11，TEXT 值中 , ; \\ 须转义"
    if "UID 重复" in problem:
        return "UID 重复", "重复 UID 会让客户端只保留其中一条"
    if "日期不存在" in problem:
        return "非法日期", "如 2 月 30 日，须为真实存在的日期"
    if "缺少" in problem:
        return "缺少字段", "UID / SUMMARY / DTSTART / DTSTAMP 为必需"
    if "无法解析" in problem or "解析失败" in problem:
        return "解析失败", "无法按内容行解析"
    return "其他", ""


def print_problems(name, problems, per_group=3):
    """按类型分组输出，避免同类问题刷屏淹没关键信息。"""
    print(f"{error('E')} {name}")
    groups = {}
    for p in problems:
        groups.setdefault(classify(p), []).append(p)
    for (category, hint), items in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        head = f"  {bold(category)} {len(items)} 条"
        if hint:
            head += f" · {hint}"
        print(head)
        for p in items[:per_group]:
            print(f"    {p}")
        if len(items) > per_group:
            print(f"    {warn(f'还有 {len(items) - per_group} 条同类')}")


def check_dist(dist):
    """检查目录下所有 ICS，返回问题总数。"""
    dist = Path(dist)
    if not dist.is_dir():
        print(error(f"目录不存在：{dist}"))
        return 1

    ics_files = sorted(dist.glob("*.ics"))
    if not ics_files:
        print(warn("没有找到 .ics 文件"))
        return 0

    total_problems = 0
    for p in ics_files:
        problems = check_ics(p)
        if problems:
            total_problems += len(problems)
            print_problems(p.name, problems)
        else:
            print(f"{ok('OK')} {p.name}")

    print()
    print(bold("== 结果 =="))
    print(f"  文件：{len(ics_files)}，问题：{total_problems}")
    return total_problems


def main():
    parser = argparse.ArgumentParser(description="检查 dist 下 ICS 合法性")
    parser.add_argument("--dist", default="dist", help="dist 目录")
    args = parser.parse_args()
    sys.exit(1 if check_dist(args.dist) else 0)


if __name__ == "__main__":
    main()
