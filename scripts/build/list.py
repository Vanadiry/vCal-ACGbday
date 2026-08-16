# list.md 生成：按作品分组输出角色列表


def _strip(s):
    return str(s).replace(" ", "").replace("　", "") if s else ""


def _char_name(char, field):
    name = (char.get("name") or {}).get(field)
    if name == 0:
        name = (char.get("name") or {}).get("orig")
    return _strip(name)


def build_list(works):
    blocks = []
    for work in works:
        info = work["info"]
        work_zh = _strip((info.get("name") or {}).get("zh"))
        work_orig = _strip((info.get("name") or {}).get("orig"))
        blocks.append(f"#### {work_zh}")
        if work_orig:
            blocks.append(f"**《{work_orig}》**  ")
        for char in work["characters"]:
            zh = _char_name(char, "zh")
            orig = _char_name(char, "orig")
            if zh and orig:
                blocks.append(f"{zh} - {orig}  ")
            elif zh:
                blocks.append(f"{zh}  ")
            elif orig:
                blocks.append(f"{orig}  ")
        blocks.append("")
    return "\n".join(blocks)
