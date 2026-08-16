# 字段引用解析：@name.zh 等


def resolve(ref, character, info):
    """解析 @ 前缀的字段引用。character 为角色数据，info 为作品数据。"""
    if not ref.startswith("@"):
        return ref
    path = ref[1:].split(".")
    if path[0] == "info":
        obj = info
        path = path[1:]
    else:
        obj = character
    for key in path:
        if not isinstance(obj, dict) or key not in obj:
            return None
        obj = obj[key]
    if obj == 0:
        obj = character.get("name", {}).get("orig")
    return obj
