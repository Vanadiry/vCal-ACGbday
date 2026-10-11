# ICS 生成：日历头部、update 事件、角色事件

from .field import resolve
from .render import render_desc


def _val(v, character, info):
    return resolve(v, character, info) if isinstance(v, str) else v


def _strip_name(name):
    return str(name).replace(" ", "").replace("　", "") if name else ""


def escape_text(value):
    """转义 TEXT 值（RFC 5545 §3.3.11）。顺序不可调换。"""
    s = str(value)
    # 必须最先处理反斜杠，否则后面新加的反斜杠会被二次转义
    s = s.replace("\\", "\\\\")
    s = s.replace(";", "\\;")
    s = s.replace(",", "\\,")
    return s.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\\n")


def fold(line, limit=75):
    """按 octet 折行（RFC 5545 §3.1）。续行以单个空格开头。

    优先在预算内最后一个转义换行处断开；找不到则按字符边界硬切。
    断点只影响可读性，客户端展开时都会还原为同一字符串。
    """
    raw = line.encode("utf-8")
    if len(raw) <= limit:
        return line
    chunks = []
    pos = 0
    first = True
    while pos < len(raw):
        budget = limit if first else limit - 1  # 续行的前导空格占 1 octet
        cut = min(pos + budget, len(raw))
        # 优先在转义换行 \n 处断开，太靠前则不用，避免浪费行
        nl = raw.rfind(b"\\n", pos, cut)
        if nl != -1 and nl - pos >= budget // 2:
            cut = nl + 2
        else:
            # 回退到字符边界：raw[cut] 为续接字节(10xxxxxx)说明切在多字节字符中间
            while cut < len(raw) and cut > pos and (raw[cut] & 0xC0) == 0x80:
                cut -= 1
            if cut == pos:
                # limit 远大于单个字符的最大字节数，此分支仅作防御
                cut = min(pos + 4, len(raw))
        chunk = raw[pos:cut].decode("utf-8")
        chunks.append(chunk if first else " " + chunk)
        pos = cut
        first = False
    return "\n".join(chunks)


def fold_lines(text, limit=75):
    """对一段以换行分隔的内容逐行折行。"""
    return "\n".join(fold(line, limit) for line in text.split("\n"))


def build_header(global_info, version_info, ics_config):
    suffix = version_info.get("suffix", "")
    prodid_name = f"{global_info['name']} {suffix}".strip()
    calname_name = f"{version_info['name']} {suffix}".strip()
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:-//{global_info['author']}//{prodid_name}//{version_info['language']}_{version_info['region']}",
        "CALSCALE:GREGORIAN",
        f"X-WR-CALNAME:{escape_text(calname_name + ' - ' + global_info['aname'])}",
        f"X-APPLE-LANGUAGE:{version_info['language']}",
        f"X-APPLE-REGION:{version_info['region']}",
        "",
    ]
    return fold_lines("\n".join(lines))


def build_update_event(global_info, ics_config, category, build_meta):
    desc_parts = [
        "version:",
        build_meta["version"],
        "",
        "website:",
        global_info["website"],
        "",
        "contributors:",
        *global_info["contributors"],
    ]
    desc = escape_text("\n".join(desc_parts))
    lines = [
        "BEGIN:VEVENT",
        f"SUMMARY;LANGUAGE=zh_CN:{escape_text(build_meta['summary'])}",
        f"DTSTART;VALUE=DATE:{build_meta['update_dtstart']}0101",
        f"DESCRIPTION:{desc}",
        f"DTSTAMP:{build_meta['dtstamp']}",
        f"CATEGORIES:{escape_text(category)}",
        "CLASS:PUBLIC",
        "TRANSP:TRANSPARENT",
        f"UID:{build_meta['uuid']}",
        "END:VEVENT",
    ]
    return fold_lines("\n".join(lines))


def build_character_event(character, info, version, ics_config, dtstamp=None):
    category = version["info"]["name"]
    name = _val(version["summary"]["field"], character, info)
    summary = f"{_strip_name(name)}{version['summary']['suffix']}"
    location = _val(version["location"], character, info) or ""

    desc = escape_text(render_desc(version["desc"], character, info))

    bday = character.get("bday", {})
    m, d = bday.get("m"), bday.get("d")
    if not m or not d:
        return None
    date = f"{ics_config['dtstart']}{m:02d}{d:02d}"

    lines = [
        "BEGIN:VEVENT",
        f"SUMMARY;LANGUAGE=zh_CN:{escape_text(summary)}",
        f"DTSTART;VALUE=DATE:{date}",
        f"LOCATION:{escape_text(location)}",
        f"DESCRIPTION:{desc}",
        f"DTSTAMP:{dtstamp}",
        f"CATEGORIES:{escape_text(category)}",
        f"RRULE:FREQ={ics_config['loop']}",
        "CLASS:PUBLIC",
        "TRANSP:TRANSPARENT",
        f"UID:{character['uuid']}",
        "BEGIN:VALARM",
        "ACTION:DISPLAY",
        f"TRIGGER:{ics_config['alarm']}",
        "END:VALARM",
        "END:VEVENT",
    ]
    return fold_lines("\n".join(lines))
