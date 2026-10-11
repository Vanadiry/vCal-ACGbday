# 清理构建产物：按 config.yml 的 tool.clean 配置删除目录。
# 目标为相对当前目录（项目根，由 vcal 入口校验）的路径。

import argparse
import shutil
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.lib.color import bold, error, info, ok, warn


def load_clean_config(config_path="config.yml"):
    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return ((config or {}).get("tool") or {}).get("clean") or {}


def collect_targets(cfg):
    """收集待删除路径，返回 [(路径, 显示名)]。不修改文件系统。"""
    target = cfg.get("target") or []
    suffix = cfg.get("suffix") or []
    skip = set(cfg.get("skip") or [])

    found = []
    seen = set()

    # 直接指定的目标
    for name in target:
        p = Path(name)
        if p.name in skip:
            continue
        if p.exists() and p not in seen:
            seen.add(p)
            found.append(p)

    # 按后缀递归查找
    if suffix:
        wanted = set(suffix)
        for p in sorted(Path(".").rglob("*")):
            if not p.is_dir() or p.name not in wanted:
                continue
            # 跳过路径上任一段命中 skip 的
            if any(part in skip for part in p.relative_to(".").parts[:-1]):
                continue
            # 已被 target 指定或已收集
            if p in seen or any(f in p.parents for f in seen):
                continue
            seen.add(p)
            found.append(p)

    return [(p, str(p)) for p in found]


def remove_targets(paths):
    removed = []
    for p in paths:
        try:
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()
            removed.append(str(p))
        except OSError as e:
            print(f"  {error('X')} {p}: {e}")
    return removed


def confirm(paths):
    """展示待删除清单并询问用户。返回是否继续。"""
    print(bold(f"将要删除 {len(paths)} 项："))
    for _, display in paths:
        print(f"  {display}")
    print()
    try:
        ans = input(f"{warn('?')} 确认删除以上 {len(paths)} 项？[y/N] ").strip().lower()
    except EOFError:
        return False
    return ans == "y"


def main():
    parser = argparse.ArgumentParser(description="清理构建产物")
    parser.add_argument("--config", default="config.yml", help="构建配置")
    parser.add_argument("--yes", action="store_true", help="跳过确认，直接删除")
    args = parser.parse_args()

    if not Path(args.config).is_file():
        print(error(f"配置文件不存在: {args.config}"))
        sys.exit(2)

    cfg = load_clean_config(args.config)
    if not cfg:
        print(warn(f"{args.config} 中没有 tool.clean 配置，无事可做"))
        return

    paths = collect_targets(cfg)
    if not paths:
        print(ok("无需清理"))
        return

    if not args.yes and not confirm(paths):
        print(info("已取消"))
        return

    print()
    removed = remove_targets([p for p, _ in paths])
    print(f"{info('已清理:')}")
    for r in removed:
        print(f"  {r}")


if __name__ == "__main__":
    main()
