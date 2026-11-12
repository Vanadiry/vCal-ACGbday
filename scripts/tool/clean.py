# Remove cache and system junk under the project root
# Use --dry-run to preview

import shutil
import sys
from fnmatch import fnmatch
from pathlib import Path

# Project root is this many levels above the script: 0 = script dir, 1 = parent
ROOT_LEVEL = 2

if ROOT_LEVEL < 0:
    raise ValueError(f"ROOT_LEVEL must be >= 0: {ROOT_LEVEL}")

ROOT = Path(__file__).resolve().parents[ROOT_LEVEL]
if str(ROOT) == ROOT.anchor:
    raise ValueError(f"ROOT_LEVEL points to the filesystem root: {ROOT}")

# Set to enforce the root directory name, empty skips the check
EXPECTED_ROOT_NAME = ""

if EXPECTED_ROOT_NAME and ROOT.name != EXPECTED_ROOT_NAME:
    raise ValueError(f"Expected root directory {EXPECTED_ROOT_NAME}, got {ROOT.name}")

DRY_RUN = "--dry-run" in sys.argv

# Directory names to remove anywhere, globs allowed
JUNK_DIRS = [
    "__pycache__",
    ".ruff_cache",
    ".pytest_cache",
    ".mypy_cache",
    ".pytype",
    ".hypothesis",
    ".ipynb_checkpoints",
    "*.egg-info",
    "htmlcov",
]

# File names to remove anywhere, globs allowed
JUNK_FILES = [
    ".DS_Store",
    "Thumbs.db",
    "desktop.ini",
    ".coverage",
    "*.pyc",
    "*.pyo",
    "._*",
]

# Paths relative to the root to remove, globs allowed (project-specific)
JUNK_PATHS = [
    "report",
]

# Directories to skip
SKIP_DIRS = [".git", ".venv", "node_modules"]


def _match(name: str, patterns: list[str]) -> bool:
    return any(fnmatch(name, pattern) for pattern in patterns)


def _should_remove(path: Path) -> bool:
    relative = path.relative_to(ROOT).as_posix()
    return (
        _match(path.name, JUNK_DIRS)
        or _match(path.name, JUNK_FILES)
        or _match(relative, JUNK_PATHS)
    )


def _raise(error: OSError) -> None:
    raise error


def main() -> None:
    if not ROOT.is_dir():
        raise NotADirectoryError(f"Project root not found: {ROOT}")

    removed_dirs = 0
    removed_files = 0
    for current, dirnames, filenames in ROOT.walk(on_error=_raise):
        dirnames[:] = [name for name in dirnames if name not in SKIP_DIRS]

        for name in list(dirnames):
            path = current / name
            if not _should_remove(path):
                continue
            print(f"  {'Would remove' if DRY_RUN else 'Removed'} dir: {path}")
            if not DRY_RUN:
                shutil.rmtree(path)
            dirnames.remove(name)
            removed_dirs += 1

        for name in filenames:
            path = current / name
            if not _should_remove(path):
                continue
            print(f"  {'Would remove' if DRY_RUN else 'Removed'} file: {path}")
            if not DRY_RUN:
                path.unlink()
            removed_files += 1

    action = "Would remove" if DRY_RUN else "Removed"
    print(f"\n{action} {removed_dirs} dirs, {removed_files} files from {ROOT}")


if __name__ == "__main__":
    main()
