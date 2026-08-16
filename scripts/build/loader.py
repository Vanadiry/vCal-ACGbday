# 数据加载：读取 data 目录下的角色与 info

from pathlib import Path

import yaml


def load_data(data_dir="data"):
    data_dir = Path(data_dir)
    works = []
    for folder in sorted(p for p in data_dir.iterdir() if p.is_dir()):
        info_file = folder / "_info.yaml"
        if not info_file.exists():
            continue
        with open(info_file, encoding="utf-8") as f:
            info = yaml.safe_load(f)
        characters = []
        for p in sorted(folder.glob("*.yml")):
            if p.name == "_info.yaml":
                continue
            with open(p, encoding="utf-8") as f:
                characters.append(yaml.safe_load(f))
        works.append({"folder": folder.name, "info": info, "characters": characters})
    return works
