# 配置加载


import yaml


def load_config(path="config.yml"):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)
