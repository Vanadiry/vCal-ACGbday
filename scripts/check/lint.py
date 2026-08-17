# 结构检查：单文件校验走 schema，全局检查保留。

import argparse
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, FormatChecker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.color import bold, error, info, ok, warn

CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

_SCHEMAS = {}


def load_schema(name):
    if name not in _SCHEMAS:
        p = Path(__file__).resolve().parents[2] / "schema" / name
        with open(p, encoding="utf-8") as f:
            schema = json.load(f)
        _SCHEMAS[name] = Draft202012Validator(schema, format_checker=FormatChecker())
    return _SCHEMAS[name]


def schema_errors(data, schema_name):  # 用 schema 校验，返回错误信息列表
    validator = load_schema(schema_name)
    errs = []
    for e in validator.iter_errors(data):
        loc = ".".join(str(p) for p in e.absolute_path) or "root"
        errs.append(f"{loc}: {e.message}")
    return errs


# 全局检查


def check_uuid_duplicates(char_files):
    by_uuid = Counter()
    for p in char_files:
        try:
            data = yaml.safe_load(p.read_text(encoding="utf-8"))
        except yaml.YAMLError:
            continue
        if isinstance(data, dict):
            u = data.get("uuid")
            if isinstance(u, str):
                by_uuid[u] += 1
    return [(u, c) for u, c in by_uuid.items() if c > 1]


def check_name_conflicts(char_files):
    by_name = {}
    for p in char_files:
        try:
            data = yaml.safe_load(p.read_text(encoding="utf-8"))
        except yaml.YAMLError:
            continue
        if not isinstance(data, dict):
            continue
        name = (data.get("name") or {}).get("zh")
        if not isinstance(name, str) or not name:
            name = (data.get("name") or {}).get("orig")
        if not isinstance(name, str) or not name:
            continue
        by_name.setdefault(name, []).append((p, data.get("uuid")))
    return [(n, items) for n, items in by_name.items() if len(items) > 1]


def check_text_safety(obj, path, errs):  # 危险字符检查
    if isinstance(obj, str):
        m = CONTROL_CHAR_RE.search(obj)
        if m:
            errs.append(f"{path}: 含控制字符 U+{ord(m.group(0)):04X}（可能导致崩溃）")
    elif isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(k, str):
                check_text_safety(k, path, errs)
            check_text_safety(v, path, errs)
    elif isinstance(obj, list):
        for item in obj:
            check_text_safety(item, path, errs)


def check_file(p, schema_name, data_dir):  # 校验单个 yml 文件，返回错误列表
    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        return [f"YAML 解析失败: {e}"]
    if not isinstance(data, dict):
        return ["顶层应为 object"]
    errs = schema_errors(data, schema_name)
    check_text_safety(data, str(p.relative_to(data_dir)), errs)
    return errs


def scan_files(data_dir: Path):
    char_files = []
    info_files = []
    for p in sorted(data_dir.rglob("*")):
        if not p.is_file() or p.suffix != ".yml":
            continue
        if p.name == "_info.yml":
            info_files.append(p)
        else:
            char_files.append(p)
    return char_files, info_files


def run_lint(data_dir, report_path):
    data_dir = Path(data_dir)
    if not data_dir.is_dir():
        print(error(f"数据目录不存在: {data_dir}"))
        return -1

    char_files, info_files = scan_files(data_dir)
    print(info(f"扫描: 角色 {len(char_files)} 个, _info {len(info_files)} 个"))

    all_errors = []
    all_warnings = []

    for p in char_files:
        rel = p.relative_to(data_dir)
        for e in check_file(p, "character.schema.json", data_dir):
            all_errors.append({"file": str(rel), "level": "error", "msg": e})
            print(f"  {error('E')} {rel}: {e}")

    for p in info_files:
        rel = p.relative_to(data_dir)
        for e in check_file(p, "info.schema.json", data_dir):
            all_errors.append({"file": str(rel), "level": "error", "msg": e})
            print(f"  {error('E')} {rel}: {e}")

    # uuid 重复
    for u, cnt in check_uuid_duplicates(char_files):
        msg = f"uuid {u} 出现 {cnt} 次（全局重复）"
        all_errors.append({"file": "全局", "level": "error", "msg": msg})
        print(f"  {error('E')} {msg}")

    # 全局命名冲突
    for name, items in check_name_conflicts(char_files):
        uuids = {i[1] for i in items}
        files = "; ".join(str(i[0].relative_to(data_dir)) for i in items)
        if len(uuids) == 1:
            msg = f"角色 {name!r} 全局重名且 uuid 相同（疑似重复文件）: {files}"
            all_errors.append({"file": files, "level": "error", "msg": msg})
            print(f"  {error('E')} {msg}")
        else:
            msg = f"角色 {name!r} 全局重名但 uuid 不同（疑似不同角色共用名）: {files}"
            all_warnings.append({"file": files, "level": "warning", "msg": msg})
            print(f"  {warn('W')} {msg}")

    # 汇总
    print()
    print(bold("== 结果汇总 =="))
    print(f"  角色文件: {len(char_files)}, _info: {len(info_files)}")
    print(f"  {error(f'错误: {len(all_errors)}')}")
    print(f"  {warn(f'警告: {len(all_warnings)}')}")
    clean_files = len(char_files) + len(info_files) - len({e["file"] for e in all_errors})
    print(f"  {ok(f'无错误文件: {clean_files}')}")

    report = {
        "generated": datetime.now().isoformat(timespec="seconds"),
        "data_dir": str(data_dir),
        "summary": {
            "character_files": len(char_files),
            "info_files": len(info_files),
            "errors": len(all_errors),
            "warnings": len(all_warnings),
        },
        "errors": all_errors,
        "warnings": all_warnings,
    }
    report_path = Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        yaml.safe_dump(report, allow_unicode=True, sort_keys=False, default_flow_style=False),
        encoding="utf-8",
    )
    print(f"\n{info(f'报告已写入: {report_path}')}")

    return len(all_errors)


def main():
    parser = argparse.ArgumentParser(description="vCal-ACGbday data lint")
    parser.add_argument("--data", default="data", help="数据目录（默认 data）")
    parser.add_argument("--report", default="report/lint_report.yml", help="报告输出路径")
    parser.add_argument("--no-color", action="store_true", help="关闭彩色输出")
    args = parser.parse_args()

    if args.no_color:
        os.environ["NO_COLOR"] = "1"

    errs = run_lint(args.data, args.report)
    sys.exit(0 if errs == 0 else 1)


if __name__ == "__main__":
    main()
