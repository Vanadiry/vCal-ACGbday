# vcal 主入口：子命令分发，透传参数

import argparse
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

PROJECT_NAME = "vcal-acgbday"


def check_project_root():
    """校验当前目录为项目根目录。返回错误信息，无误则返回 None。

    以 pyproject.toml 的 project.name 为准而非目录名：
    目录名会随 fork、clone 改名而变化，pyproject 内容不会。
    """
    p = Path("pyproject.toml")
    if not p.is_file():
        return f"当前目录不是项目根目录，因为未找到 {p}，请 cd 到项目目录后再执行"
    with open(p, "rb") as f:
        name = tomllib.load(f)["project"]["name"]
    if name != PROJECT_NAME:
        return f"当前目录的项目名 {name!r} 不是 {PROJECT_NAME!r}，请 cd 到项目目录后再执行"
    return None


def main():
    err = check_project_root()
    if err:
        print(f"vcal: {err}", file=sys.stderr)
        sys.exit(2)

    parser = argparse.ArgumentParser(prog="vcal", description="vCal-ACGbday 工具")
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check", help="检查数据与产物")
    check_sub = check.add_subparsers(dest="check_target", required=True)

    # 叶子子命令本身不带参数，其自动添加的 -h/--help 会遮蔽真实命令的 --help
    # 故关闭，让 --help 透传给实际处理该命令的模块
    check_sub.add_parser("lint", help="结构检查", add_help=False)
    check_sub.add_parser("uuid", help="uuid 标准化", add_help=False)
    check_sub.add_parser("bday", help="生日数据检查", add_help=False)
    check_sub.add_parser("dist", help="检查 dist 产物", add_help=False)

    sub.add_parser("build", help="构建产物", add_help=False)

    imp = sub.add_parser("import", help="数据导入")
    imp_sub = imp.add_subparsers(dest="import_target", required=True)
    imp_sub.add_parser("fill", help="从 bangumi 补全缺失角色", add_help=False)
    imp_sub.add_parser("tracker", help="从 tracker.yml 拉取整部作品", add_help=False)

    tool = sub.add_parser("tool", help="其他工具")
    tool_sub = tool.add_subparsers(dest="tool_target", required=True)
    tool_sub.add_parser("clean", help="清理构建产物", add_help=False)

    args, rest = parser.parse_known_args()

    handlers = {
        ("check", "lint"): ("scripts.check.lint", "main"),
        ("check", "uuid"): ("scripts.check.normalize_uuid", "main"),
        ("check", "bday"): ("scripts.check.bday", "main"),
        ("check", "dist"): ("scripts.check.dist_ics", "main"),
        ("build",): ("scripts.build.build", "main"),
        ("import", "fill"): ("scripts.import.fill", "main"),
        ("import", "tracker"): ("scripts.import.tracker", "main"),
        ("tool", "clean"): ("scripts.tool.clean", "main"),
    }

    key = (args.command,)
    if args.command == "check":
        key = (args.command, args.check_target)
    elif args.command == "import":
        key = (args.command, args.import_target)
    elif args.command == "tool":
        key = (args.command, args.tool_target)

    if key not in handlers:
        parser.print_help()
        sys.exit(2)

    module_name, func_name = handlers[key]
    module = __import__(module_name, fromlist=[func_name])
    func = getattr(module, func_name)
    sys.argv = ["vcal"] + rest
    func()


if __name__ == "__main__":
    main()
