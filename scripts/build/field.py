# 字段引用解析：@name.zh 等


def resolve(ref, character, info):
    """解析 @ 前缀的字段引用。character 为角色数据，info 为作品数据。"""
    if not ref.startswith("@"):
        return ref
    path = ref[1:].split(".")
    if path[0] == "info":
        root = info
        path = path[1:]
    else:
        root = character
    obj = root
    for key in path:
        if not isinstance(obj, dict) or key not in obj:
            return None
        obj = obj[key]
    if type(obj) is int and obj == 0:
        # 0 表示该语言的名称等同于本条目自身的 orig，无需另填
        return (root.get("name") or {}).get("orig")
    return obj
