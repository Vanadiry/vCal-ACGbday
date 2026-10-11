# 构建配置检查：按 schema 校验 config.yml，并补充 schema 无法表达的跨条目检查。

import json
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.lib.color import error, info, ok

_SCHEMAS = {}


def load_schema(name):
    if name not in _SCHEMAS:
        p = Path(__file__).resolve().parents[2] / "schema" / name
        with open(p, encoding="utf-8") as f:
            _SCHEMAS[name] = Draft202012Validator(json.load(f))
    return _SCHEMAS[name]


def check_schema(config, schema_name):  # 返回错误信息列表
    errs = []
    for e in load_schema(schema_name).iter_errors(config):
        loc = ".".join(str(p) for p in e.absolute_path) or "root"
        errs.append(f"{loc}: {e.message}")
    return errs


def check_output_collisions(config):  # 返回错误信息列表
    """产物文件名冲突。JSON Schema 无法表达"任意两条目派生值不得相同"，在此检查。"""
    errs = []
    for section, key in (("ics", "info"), ("js", None)):
        base = (config.get("global", {}).get("ics") or {}).get("file") or ""
        seen = {}
        for name, version in (config.get(section) or {}).items():
            suffix = (version.get(key) or {}).get("file", "") if key else version.get("file", "")
            if not isinstance(suffix, str):
                continue  # 类型错误交给 schema
            fname = f"{base}{suffix}.{section}"
            if fname in seen:
                errs.append(f"{section}: 版本 {name!r} 与 {seen[fname]!r} 的产物同名: {fname}")
            else:
                seen[fname] = name
    return errs


def run_config_check(config_path="config.yml"):
    """校验构建配置。返回错误数（0 表示通过）。"""
    config_path = Path(config_path)
    if not config_path.is_file():
        print(error(f"配置文件不存在: {config_path}"))
        return 1

    try:
        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        print(f"  {error('E')} {config_path}: YAML 解析失败: {e}")
        return 1

    if not isinstance(config, dict):
        print(f"  {error('E')} {config_path}: 顶层应为 object")
        return 1

    print(info(f"配置检查: {config_path}"))

    errs = check_schema(config, "config.schema.json")
    errs += check_output_collisions(config)

    for e in errs:
        print(f"  {error('E')} {e}")
    print(f"  {ok('配置检查通过')}" if not errs else "")

    print()
    print(f"  {error(f'配置错误: {len(errs)}')}")
    return len(errs)
