# ICS 生成：日历头部、update 事件、角色事件

from .field import resolve
from .render import render_desc


def _val(v, character, info):
    return resolve(v, character, info) if isinstance(v, str) else v


def _strip_name(name):
    return str(name).replace(" ", "").replace("　", "") if name else ""


def build_header(global_info, version_info, ics_config):
    suffix = version_info.get("suffix", "")
    prodid_name = f"{global_info['name']} {suffix}".strip()
    calname_name = f"{version_info['name']} {suffix}".strip()
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:-//{global_info['author']}//{prodid_name}//{version_info['language']}_{version_info['region']}",
        "CALSCALE:GREGORIAN",
        f"X-WR-CALNAME:{calname_name} - {global_info['aname']}",
        f"X-APPLE-LANGUAGE:{version_info['language']}",
        f"X-APPLE-REGION:{version_info['region']}",
        "",
    ]
    return "\n".join(lines)


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
    desc = "\\n".join(desc_parts)
    lines = [
        "BEGIN:VEVENT",
        f"SUMMARY;LANGUAGE=zh_CN:{build_meta['summary']}",
        f"DTSTART;VALUE=DATE:{build_meta['update_dtstart']}0101",
        f"DESCRIPTION:{desc}",
        f"DTSTAMP;VALUE=DATE:{build_meta['dtstamp']}",
        f"CATEGORIES:{category}",
        "CLASS:PUBLIC",
        "TRANSP:TRANSPARENT",
        f"UID:{build_meta['uuid']}",
        "END:VEVENT",
    ]
    return "\n".join(lines)


def build_character_event(character, info, version, ics_config, dtstamp=None):
    category = version["info"]["name"]
    name = _val(version["summary"]["field"], character, info)
    summary = f"{_strip_name(name)}{version['summary']['suffix']}"
    location = _val(version["location"], character, info) or ""

    desc = render_desc(version["desc"], character, info).replace("\n", "\\n")

    bday = character.get("bday", {})
    m, d = bday.get("m"), bday.get("d")
    if not m or not d:
        return None
    date = f"{ics_config['dtstart']}{m:02d}{d:02d}"

    lines = [
        "BEGIN:VEVENT",
        f"SUMMARY;LANGUAGE=zh_CN:{summary}",
        f"DTSTART;VALUE=DATE:{date}",
        f"LOCATION:{location}",
        f"DESCRIPTION:{desc}",
        f"DTSTAMP;VALUE=DATE:{dtstamp}",
        f"CATEGORIES:{category}",
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
    return "\n".join(lines)
