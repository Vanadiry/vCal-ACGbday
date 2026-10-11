# 数据文件的行内编辑：只改动目标字段所在行，其余内容逐字节保留。
# 用于避免 yaml.dump 整体重写时丢失注释与原有格式。

import re


def _find_block(lines, block_key):
    """定位顶层块（如 bday）的起止行号，返回 (起始行下标, 结束行下标，不含结束)。

    起始行是 block_key 所在行；结束行是其后第一个缩进为空的非空行。
    """
    start = None
    for i, line in enumerate(lines):
        if line.rstrip() == block_key:
            start = i
            break
    if start is None:
        return None
    end = len(lines)
    for j in range(start + 1, len(lines)):
        stripped = lines[j].strip()
        if stripped and not lines[j].startswith((" ", "\t")):
            end = j
            break
    return start, end


def set_scalar(path, block_key, field, value):
    """在文件的 block_key 块内设置 field 字段。

    field 已存在则替换该行；不存在则在块内最后一个字段之后插入。
    返回 True 表示文件有改动。
    """
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")

    if not block_key:
        # 顶层字段（如 uuid），行首不得有缩进
        pattern = re.compile(rf"^{re.escape(field)}\s*:")
        for i, line in enumerate(lines):
            if pattern.match(line):
                lines[i] = f"{field}: {value}"
                break
        else:
            return False
        new_text = "\n".join(lines)
        if new_text == text:
            return False
        path.write_text(new_text, encoding="utf-8")
        return True

    block = _find_block(lines, block_key)
    if block is None:
        return False
    start, end = block

    pattern = re.compile(rf"^(\s*){re.escape(field)}\s*:")
    last_field = None
    for i in range(start + 1, end):
        m = pattern.match(lines[i])
        if m:
            lines[i] = f"{m.group(1)}{field}: {value}"
            break
        if lines[i].strip():
            last_field = i
    else:
        # 字段不存在，插到块内最后一个字段之后
        if last_field is None:
            lines.insert(end, f"  {field}: {value}")
        else:
            indent = re.match(r"^(\s*)", lines[last_field]).group(1)
            lines.insert(last_field + 1, f"{indent}{field}: {value}")

    new_text = "\n".join(lines)
    if new_text == text:
        return False
    path.write_text(new_text, encoding="utf-8")
    return True
