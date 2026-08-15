import argparse
import os
import re
import sys
import uuid as uuid_mod
from collections import Counter
from datetime import datetime
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.color import bold, error, info, ok, warn

# 常量

LANG_KEY_RE = re.compile(r"^[a-z]{2}(-[a-z]+)?$")
WIKI_KEY_RE = re.compile(r"^wikipedia-[a-z]+(-[a-z0-9]+)*$")
UUID_FMT_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

CHAR_REQUIRED = ["name", "bday", "uuid"]
INFO_REQUIRED = ["name", "id"]
CHAR_ALLOWED = {"name", "desc", "bday", "uuid", "refs"}
INFO_ALLOWED = {"name", "id"}


class LintResult:
    def __init__(self):
        self.errors = []
        self.warnings = []


# 空值检查


def is_empty_value(v):  # 空串 / 空列表 / None 视为空值
    if v is None:
        return True
    if isinstance(v, str):
        return not v.strip()
    if isinstance(v, list):
        return len(v) == 0
    if isinstance(v, dict):
        return len(v) == 0
    return False


def check_empty_fields(obj, result, path, prefix=""):  # 递归检查空值字段
    if isinstance(obj, dict):
        for k, v in obj.items():
            full = f"{prefix}.{k}" if prefix else f"..{k}"
            if is_empty_value(v):
                result.errors.append(
                    f"{path}: {full} 为空值（{describe_empty(v)}），应删除该键或补全内容"
                )
            else:
                check_empty_fields(v, result, path, full)
    elif isinstance(obj, list):
        for idx, v in enumerate(obj):
            check_empty_fields(v, result, path, f"{prefix}[{idx}]")


def describe_empty(v):
    if v is None:
        return "null"
    if isinstance(v, str):
        return "空字符串"
    if isinstance(v, list):
        return "空列表"
    if isinstance(v, dict):
        return "空字典"
    return "空值"


# 字段检查


def check_name(name, result, path):
    if not isinstance(name, dict):
        result.errors.append(f"{path}: name 应为 object，实际 {type(name).__name__}")
        return
    if "orig" not in name:
        result.errors.append(f"{path}: name.orig 缺失（必填）")
    else:
        orig = name["orig"]
        if not isinstance(orig, str) or not orig.strip():
            result.errors.append(f"{path}: name.orig 应为非空字符串，实际 {orig!r}")
    for k, v in name.items():
        if k == "orig":
            continue
        if not LANG_KEY_RE.match(k):
            result.errors.append(f"{path}: name.{k} 不是合法语言键")
            continue
        if isinstance(v, int):
            if v != 0:
                result.errors.append(f"{path}: name.{k} 数值只能是 0（表示等于 orig）")
        elif not isinstance(v, str):
            result.errors.append(f"{path}: name.{k} 应为 0 或字符串，实际 {v!r}")


def check_desc(desc, result, path):
    if not isinstance(desc, dict):
        result.errors.append(f"{path}: desc 应为 object，实际 {type(desc).__name__}")
        return
    for k, v in desc.items():
        if k == "extra":
            if not isinstance(v, list):
                result.errors.append(f"{path}: desc.extra 应为数组")
            else:
                for i, item in enumerate(v):
                    if not isinstance(item, str) or not item.strip():
                        result.errors.append(f"{path}: desc.extra[{i}] 应为非空字符串")
        elif k == "main":
            if not isinstance(v, str):
                result.errors.append(f"{path}: desc.main 应为字符串")
        else:
            result.errors.append(f"{path}: desc 存在未知键 {k!r}")


def check_bday(bday, result, path):
    if not isinstance(bday, dict):
        result.errors.append(f"{path}: bday 应为 object，实际 {type(bday).__name__}")
        return
    for k in ("m", "d"):
        if k not in bday:
            result.errors.append(f"{path}: bday.{k} 缺失（必填）")
            continue
        v = bday[k]
        if not isinstance(v, int) or isinstance(v, bool):
            result.errors.append(f"{path}: bday.{k} 应为整数，实际 {v!r}")
            continue
        lo, hi = (1, 12) if k == "m" else (1, 31)
        if not (lo <= v <= hi):
            result.errors.append(f"{path}: bday.{k}={v} 超出范围 {lo}-{hi}")
    if "y" in bday:
        v = bday["y"]
        if v is None:
            result.errors.append(f"{path}: bday.y 为 null，应删除该键")
        elif not isinstance(v, int) or isinstance(v, bool) or v < 1:
            result.errors.append(f"{path}: bday.y 应为正整数，实际 {v!r}")
    if "verified" in bday and not isinstance(bday["verified"], bool):
        result.errors.append(f"{path}: bday.verified 应为布尔值，实际 {bday['verified']!r}")


def check_refs(refs, result, path):
    if not isinstance(refs, dict):
        result.errors.append(f"{path}: refs 应为 object，实际 {type(refs).__name__}")
        return
    if not refs:
        result.errors.append(f"{path}: refs 为空 dict，至少需要一个数据源引用")
        return
    for k, v in refs.items():
        if k == "bangumi":
            if isinstance(v, int):
                if v < 1:
                    result.errors.append(f"{path}: refs.bangumi 应为正整数")
            elif isinstance(v, str):
                if not v.isdigit() or not v:
                    result.errors.append(f"{path}: refs.bangumi 字符串应为纯数字")
            else:
                result.errors.append(f"{path}: refs.bangumi 应为整数或数字字符串")
        elif k == "moegirl":
            if not isinstance(v, str):
                result.errors.append(f"{path}: refs.moegirl 应为字符串")
        elif WIKI_KEY_RE.match(k):
            if not isinstance(v, str):
                result.errors.append(f"{path}: refs.{k} 应为字符串")
        else:
            result.errors.append(f"{path}: refs 存在未知键 {k!r}")


def check_uuid(value, result, path):
    if not isinstance(value, str):
        result.errors.append(f"{path}: uuid 应为字符串，实际 {type(value).__name__}")
        return
    if not UUID_FMT_RE.match(value):
        result.errors.append(f"{path}: uuid 格式非法（需 8-4-4-4-12 hex）：{value!r}")
        return
    # 格式合法，校验版本位（仅提示，历史数据版本位非 1-5）
    try:
        u = uuid_mod.UUID(value)
        if u.version not in (1, 2, 3, 4, 5):
            result.warnings.append(f"{path}: uuid 版本位为 {u.version}（非标准 1-5，仅提示）")
    except ValueError:
        result.errors.append(f"{path}: uuid 解析失败：{value!r}")


def check_text_safety(text, result, path):
    if not isinstance(text, str):
        return
    m = CONTROL_CHAR_RE.search(text)
    if m:
        result.errors.append(f"{path}: 含控制字符 U+{ord(m.group(0)):04X}（可能导致崩溃）")


# 文件级检查


def check_character_file(path: Path):
    result = LintResult()
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        result.errors.append(f"{path}: YAML 解析失败: {e}")
        return result

    if not isinstance(data, dict):
        result.errors.append(f"{path}: 顶层应为 object，实际 {type(data).__name__}")
        return result

    for key in CHAR_REQUIRED:
        if key not in data:
            result.errors.append(f"{path}: 缺少必填 key {key!r}")
    for k in data:
        if k not in CHAR_ALLOWED:
            result.errors.append(f"{path}: 未知顶层键 {k!r}")

    if "name" in data:
        check_name(data["name"], result, path)
    if "desc" in data:
        check_desc(data["desc"], result, path)
    if "bday" in data:
        check_bday(data["bday"], result, path)
    if "uuid" in data:
        check_uuid(data["uuid"], result, path)
    if "refs" in data:
        check_refs(data["refs"], result, path)
    else:
        result.errors.append(f"{path}: 缺少必填 key 'refs'（至少需一个数据源引用）")

    check_empty_fields(data, result, path)

    def walk(obj):
        if isinstance(obj, str):
            check_text_safety(obj, result, path)
        elif isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(k, str):
                    check_text_safety(k, result, path)
                walk(v)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(data)
    return result


def check_info_file(path: Path):
    result = LintResult()
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        result.errors.append(f"{path}: YAML 解析失败: {e}")
        return result

    if not isinstance(data, dict):
        result.errors.append(f"{path}: 顶层应为 object")
        return result

    for key in INFO_REQUIRED:
        if key not in data:
            result.errors.append(f"{path}: 缺少必填 key {key!r}")
    for k in data:
        if k not in INFO_ALLOWED:
            result.errors.append(f"{path}: 未知顶层键 {k!r}")

    if "name" in data:
        check_name(data["name"], result, path)
    if "id" in data:
        i = data["id"]
        if not isinstance(i, dict):
            result.errors.append(f"{path}: id 应为 object")
        else:
            has_b, has_c, has_m = "bangumi" in i, "custom" in i, "moegirl" in i
            if not (has_b or has_c or has_m):
                result.errors.append(f"{path}: id 至少需要 bangumi / custom / moegirl 之一")
            for k in i:
                if k not in ("bangumi", "custom", "moegirl"):
                    result.errors.append(f"{path}: id 存在未知键 {k!r}")
            if has_b:
                b = i["bangumi"]
                if not isinstance(b, list):
                    result.errors.append(f"{path}: id.bangumi 应为数组")
                else:
                    if not b:
                        result.errors.append(f"{path}: id.bangumi 数组为空")
                    for idx, item in enumerate(b):
                        if not isinstance(item, int) or isinstance(item, bool) or item < 1:
                            result.errors.append(f"{path}: id.bangumi[{idx}] 应为正整数")
                    if len(set(b)) != len(b):
                        result.errors.append(f"{path}: id.bangumi 存在重复 id")
            if has_c:
                c = i["custom"]
                if not isinstance(c, int) or isinstance(c, bool) or c < 1:
                    result.errors.append(f"{path}: id.custom 应为正整数")
            if has_m:
                m = i["moegirl"]
                if not isinstance(m, list):
                    result.errors.append(f"{path}: id.moegirl 应为数组")
                else:
                    if not m:
                        result.errors.append(f"{path}: id.moegirl 数组为空")
                    for idx, item in enumerate(m):
                        if not isinstance(item, str) or not item.strip():
                            result.errors.append(f"{path}: id.moegirl[{idx}] 应为非空字符串")
                    if len(set(m)) != len(m):
                        result.errors.append(f"{path}: id.moegirl 存在重复页面名")

    check_empty_fields(data, result, path)

    def walk(obj):
        if isinstance(obj, str):
            check_text_safety(obj, result, path)
        elif isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(k, str):
                    check_text_safety(k, result, path)
                walk(v)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(data)
    return result


# 全局检查


def check_uuid_duplicates(char_files):  # 全局 uuid 查重
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


def check_name_conflicts(char_files):  # uuid 相同=重复，不同=共用名提醒
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


# 主流程


def scan_files(data_dir: Path):
    char_files = []
    info_files = []
    for p in sorted(data_dir.rglob("*")):
        if not p.is_file() or p.suffix not in (".yml", ".yaml"):
            continue
        if p.name in ("_info.yaml", "_info.yml"):
            info_files.append(p)
        else:
            char_files.append(p)
    return char_files, info_files


def run_lint(data_dir, report_path):
    """执行 lint 检查。返回错误数（0 = 通过）。"""
    data_dir = Path(data_dir)
    if not data_dir.is_dir():
        print(error(f"数据目录不存在: {data_dir}"))
        return -1

    char_files, info_files = scan_files(data_dir)
    print(info(f"扫描: 角色 {len(char_files)} 个, _info {len(info_files)} 个"))

    all_errors = []
    all_warnings = []

    for p in char_files:
        r = check_character_file(p)
        rel = p.relative_to(data_dir)
        for e in r.errors:
            all_errors.append({"file": str(rel), "level": "error", "msg": e})
            print(f"  {error('E')} {rel}: {e}")
        for w in r.warnings:
            all_warnings.append({"file": str(rel), "level": "warning", "msg": w})
            print(f"  {warn('W')} {rel}: {w}")

    for p in info_files:
        r = check_info_file(p)
        rel = p.relative_to(data_dir)
        for e in r.errors:
            all_errors.append({"file": str(rel), "level": "error", "msg": e})
            print(f"  {error('E')} {rel}: {e}")
        for w in r.warnings:
            all_warnings.append({"file": str(rel), "level": "warning", "msg": w})
            print(f"  {warn('W')} {rel}: {w}")

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
