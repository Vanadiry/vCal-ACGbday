# 数据加载：读取 data 目录下的角色与 info

from pathlib import Path

import yaml


def _work_key(info):
    ids = (info.get("id") or {}).get("bangumi") or []
    return ids[0] if ids else 0


def _char_key(char):
    bday = char.get("bday") or {}
    name = (char.get("name") or {}).get("zh") or (char.get("name") or {}).get("orig") or ""
    return (bday.get("m", 0), bday.get("d", 0), name)


def load_data(data_dir="data"):
    data_dir = Path(data_dir)
    works = []
    for folder in data_dir.iterdir():
        if not folder.is_dir():
            continue
        info_file = folder / "_info.yml"
        if not info_file.exists():
            continue
        with open(info_file, encoding="utf-8") as f:
            info = yaml.safe_load(f)
        characters = []
        for p in folder.glob("*.yml"):
            if p.name == "_info.yml":
                continue
            with open(p, encoding="utf-8") as f:
                characters.append(yaml.safe_load(f))
        characters.sort(key=_char_key)
        works.append({"folder": folder.name, "info": info, "characters": characters})
    works.sort(key=lambda w: _work_key(w["info"]))
    return works
