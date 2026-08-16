# desc 渲染：按 config 的 block/line 结构组织

from .field import resolve


def _join_line(parts):
    return "／".join(p for p in parts if p)


def render_desc(desc_config, character, info):
    """按 config 渲染角色描述。返回多行字符串（行间 \n，块间 \n\n）。"""
    blocks = []
    for block in desc_config:
        block_lines = []
        for item in block.get("block", []):
            if isinstance(item, str):
                # 直接字符串引用
                val = resolve(item, character, info)
                if val is None:
                    continue
                if isinstance(val, list):
                    block_lines.extend(v for v in val if v)
                elif val:
                    block_lines.append(val)
            elif isinstance(item, dict):
                if "line" in item:
                    parts = []
                    for f in item["line"]:
                        val = resolve(f, character, info)
                        if val is None:
                            continue
                        if isinstance(val, list):
                            for v in val:
                                if v:
                                    block_lines.append(v)
                        elif val:
                            parts.append(str(val))
                    if parts:
                        block_lines.append(_join_line(parts))
                elif "field" in item:
                    val = resolve(item["field"], character, info)
                    bracket = item.get("bracket", "")
                    if val is None:
                        continue
                    if isinstance(val, list):
                        for v in val:
                            if v:
                                block_lines.append(f"{bracket[0]}{v}{bracket[1]}")
                    elif val:
                        block_lines.append(f"{bracket[0]}{val}{bracket[1]}")
        if block_lines:
            blocks.append("\n".join(block_lines))
    return "\n\n".join(blocks)
