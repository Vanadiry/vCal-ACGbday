# 将版本位非 1-5 的 uuid 重写为标准 v4（小写）

import argparse
import os
import re
import sys
import uuid as uuid_mod
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.color import error, info, ok, warn

UUID_FMT_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


class BlockDumper(yaml.SafeDumper):
    pass


def str_rep(dumper, data):
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


def main():
    BlockDumper.add_representer(str, str_rep)

    parser = argparse.ArgumentParser(description="标准化 uuid 为 v4（小写）")
    parser.add_argument("--data", default="data", help="数据目录（默认 data）")
    parser.add_argument("--no-color", action="store_true", help="关闭彩色输出")
    args = parser.parse_args()

    if args.no_color:
        os.environ["NO_COLOR"] = "1"

    data_dir = Path(args.data)
    if not data_dir.is_dir():
        print(error(f"数据目录不存在: {data_dir}"))
        sys.exit(2)

    invalid = []
    files = [p for p in data_dir.rglob("*.yml") if p.is_file() and p.name != "_info.yaml"]

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
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
        new_uuid = str(uuid_mod.uuid4()).lower()
        data["uuid"] = new_uuid
        p.write_text(
            yaml.dump(
                data,
                Dumper=BlockDumper,
                allow_unicode=True,
                sort_keys=False,
                default_flow_style=False,
            ),
            encoding="utf-8",
        )
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
