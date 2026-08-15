# 清理构建产物：report/ __pycache__/ *.egg-info/ .ruff_cache/
# 以脚本位置的上一级目录作为项目根目录

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGETS = ["report", ".ruff_cache"]
SUFFIXES = ("__pycache__", ".egg-info")
SKIP_DIRS = {".venv", ".git"}


def main():
    removed = []
    for name in TARGETS:
        p = ROOT / name
        if p.exists():
            shutil.rmtree(p)
            removed.append(str(p))
    for p in ROOT.rglob("*"):
        if (
            p.is_dir()
            and p.name.endswith(SUFFIXES)
            and not any(part in SKIP_DIRS for part in p.relative_to(ROOT).parts)
        ):
            shutil.rmtree(p)
            removed.append(str(p))
    if removed:
        print("已清理:")
        for r in removed:
            print(f"  {r}")
    else:
        print("无需清理")


if __name__ == "__main__":
    main()
