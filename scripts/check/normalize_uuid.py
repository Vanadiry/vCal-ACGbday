# 将版本位非 1-5 的 uuid 重写为标准 v4（小写）

import argparse
import re
import sys
import uuid as uuid_mod
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.lib.color import error, info, ok, warn
from scripts.lib.yaml_edit import set_scalar

UUID_FMT_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def main():
    parser = argparse.ArgumentParser(description="标准化 uuid 为 v4（小写）")
    parser.add_argument("--data", default="data", help="数据目录（默认 data）")
    args = parser.parse_args()

    data_dir = Path(args.data)
    if not data_dir.is_dir():
        print(error(f"数据目录不存在: {data_dir}"))
        sys.exit(2)

    invalid = []
    files = [p for p in data_dir.rglob("*.yml") if p.is_file() and p.name != "_info.yml"]

    for p in files:
        try:
            data = yaml.safe_load(p.read_text(encoding="utf-8"))
        except yaml.YAMLError:
            continue
        if not isinstance(data, dict):
            continue
        u = data.get("uuid")
        if not isinstance(u, str):
            invalid.append((p, u, "非字符串"))
            continue
        if not UUID_FMT_RE.match(u):
            invalid.append((p, u, "格式非法"))
            continue
        try:
            ver = uuid_mod.UUID(u).version
        except ValueError:
            invalid.append((p, u, "解析失败"))
            continue
        if ver not in (1, 2, 3, 4, 5):
            invalid.append((p, u, f"版本位 {ver}"))

    print(info(f"扫描: {len(files)} 个角色文件, 不合规 uuid: {len(invalid)} 个"))

    if not invalid:
        print(ok("无不合规 uuid"))
        return

    for p, old, why in invalid:
        print(f"  {warn(why)} {p.relative_to(data_dir)}: {old}")

    rewritten = 0
    for p, _old, _why in invalid:
        new_uuid = str(uuid_mod.uuid4()).lower()
        if set_scalar(p, "", "uuid", new_uuid):
            rewritten += 1

    print(f"\n{ok(f'已重写 {rewritten} 个 uuid')}")

    # 重写后查重
    seen = {}
    dup = []
    for p in files:
        try:
            data = yaml.safe_load(p.read_text(encoding="utf-8"))
        except yaml.YAMLError:
            continue
        if isinstance(data, dict) and isinstance(data.get("uuid"), str):
            u = data["uuid"]
            if u in seen:
                dup.append((seen[u], p, u))
            else:
                seen[u] = p
    if dup:
        print(warn(f"重写后出现 {len(dup)} 处 uuid 重复:"))
        for a, b, u in dup:
            print(f"  {u}: {a.relative_to(data_dir)} <-> {b.relative_to(data_dir)}")
    else:
        print(ok("重写后无 uuid 重复"))


if __name__ == "__main__":
    main()
