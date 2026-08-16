# vcal 主入口：子命令分发，透传参数

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def main():
    parser = argparse.ArgumentParser(prog="vcal", description="vCal-ACGbday 工具")
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check", help="检查数据与产物")
    check_sub = check.add_subparsers(dest="check_target", required=True)

    check_sub.add_parser("lint", help="结构检查")
    check_sub.add_parser("uuid", help="uuid 标准化")
    check_sub.add_parser("bday", help="生日数据检查")
    check_sub.add_parser("dist", help="检查 dist 产物")

    sub.add_parser("build", help="构建产物")

    imp = sub.add_parser("import", help="数据导入")
    imp_sub = imp.add_subparsers(dest="import_target", required=True)
    imp_sub.add_parser("fill", help="从 bangumi 补全缺失角色")

    args, rest = parser.parse_known_args()

    handlers = {
        ("check", "lint"): ("scripts.check.lint", "main"),
        ("check", "uuid"): ("scripts.check.normalize_uuid", "main"),
        ("check", "bday"): ("scripts.check.bday", "main"),
        ("check", "dist"): ("scripts.check.dist_ics", "main"),
        ("build",): ("scripts.build.build", "main"),
        ("import", "fill"): ("scripts.import.fill", "main"),
    }

    key = (args.command,)
    if args.command == "check":
        key = (args.command, args.check_target)
    elif args.command == "import":
        key = (args.command, args.import_target)

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
