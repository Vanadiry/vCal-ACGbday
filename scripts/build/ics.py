# ICS 生成：日历头部、update 事件、角色事件

from .field import resolve
from .render import render_desc


def _val(v, character, info):
    return resolve(v, character, info) if isinstance(v, str) else v


def _strip_name(name):
    return str(name).replace(" ", "").replace("　", "") if name else ""


def build_header(global_info, version_info, ics_config):
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:-//{global_info['author']}//{global_info['name']}//{version_info['language']}_{version_info['region']}",
        "CALSCALE:GREGORIAN",
        f"X-WR-CALNAME:{version_info['name']} - {global_info['aname']}",
        f"X-APPLE-LANGUAGE:{version_info['language']}",
        f"X-APPLE-REGION:{version_info['region']}",
        "",
    ]
    return "\n".join(lines)


def build_update_event(global_info, ics_config, category):
    update = ics_config["update"]
    desc_parts = [
        "version:",
        update["version"],
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
        f"SUMMARY;LANGUAGE=zh_CN:{update['summary']}",
        f"DTSTART;VALUE=DATE:{update['dtstart']}0101",
        f"DESCRIPTION:{desc}",
        f"DTSTAMP;VALUE=DATE:{ics_config['dtstamp']}0101",
        f"CATEGORIES:{category}",
        "CLASS:PUBLIC",
        "TRANSP:TRANSPARENT",
        f"UID:{update['uuid']}",
        "END:VEVENT",
    ]
    return "\n".join(lines)


def build_character_event(character, info, version, ics_config):
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
        f"DTSTAMP;VALUE=DATE:{ics_config['dtstamp']}0101",
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
