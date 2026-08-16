# JS 生成：按作品分组的今日生日查询脚本

import json

from .field import resolve


def _strip(s):
    return str(s).replace(" ", "").replace("　", "") if s else ""


def _resolve(ref, character, info, strip=True):
    val = resolve(ref, character, info)
    return _strip(val) if strip else str(val) if val else ""


def build_grouped(works, character_field, location_field):
    grouped = {}
    for work in works:
        info = work["info"]
        origin = _resolve(location_field, {}, info, strip=False)
        if not origin:
            continue
        items = []
        for char in work["characters"]:
            bday = char.get("bday") or {}
            m, d = bday.get("m"), bday.get("d")
            if not m or not d:
                continue
            name = _resolve(character_field, char, info)
            if not name:
                continue
            items.append([name, f"{m:02d}{d:02d}"])
        if items:
            grouped[origin] = items
    return grouped


def build_js(works, version, version_name, global_info, global_config):
    grouped = build_grouped(works, version["character"], version["location"])

    header = f"// {global_info['name']} - {version_name}\n// By {global_info['author']}\n\n"

    lines = ["const works = {"]
    for origin, chars in grouped.items():
        lines.append(f"  {json.dumps(origin, ensure_ascii=False)}: [")
        for name, bday in chars:
            lines.append(f"    [{json.dumps(name, ensure_ascii=False)}, {json.dumps(bday)}],")
        lines.append("  ],")
    lines.append("};")
    body = "\n".join(lines)

    notfound = global_config["js"]["notfound"]
    footer = f"""

(function () {{
    const today = new Date();
    const date =
        `${{today.getMonth() + 1}}`.padStart(2, "0") +
        `${{today.getDate()}}`.padStart(2, "0");
    let out = [];
    for (const [o, cs] of Object.entries(works))
        for (const [n, b] of cs)
            if (b === date) out.push(`${{n}} <span style="color:#888">[${{o}}]</span>`);
    const el = document.getElementById("result");
    if (!el) {{
        console.error("Element with id 'result' not found.");
        return;
    }}
    el.innerHTML = out.length ? out.join("<br>") : "{notfound}";
}})();
"""
    return header + body + footer
