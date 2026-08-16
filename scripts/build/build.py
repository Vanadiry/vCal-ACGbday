# 构建入口：根据 config.yml 生成 ICS 文件

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "check"))
from check.lint import run_lint

from .config import load_config
from .ics import build_character_event, build_header, build_update_event
from .loader import load_data


def build_version(version_name, version, global_info, ics_config, works):
    events = []
    for work in works:
        info = work["info"]
        for character in work["characters"]:
            ev = build_character_event(character, info, version, ics_config)
            if ev:
                events.append(ev)
    header = build_header(global_info, version["info"], ics_config)
    update = build_update_event(global_info, ics_config, version["info"]["name"])
    content = "\n\n".join([header, update, *events]) + "\nEND:VCALENDAR"
    return content


def main():
    parser = argparse.ArgumentParser(description="构建 ICS 文件")
    parser.add_argument("--config", default="config.yml")
    parser.add_argument("--data", default="data")
    parser.add_argument("--output", default="dist")
    args = parser.parse_args()

    # 前置 lint 检查，不通过则终止
    lint_errs = run_lint(args.data, "report/lint_report.yml")
    if lint_errs != 0:
        print("\nlint 检查未通过，请先修正数据再构建")
        sys.exit(1)

    config = load_config(args.config)
    works = load_data(args.data)
    global_info = config["global"]["info"]
    ics_config = config["global"]["ics"]
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    for version_name, version in config["ics"].items():
        content = build_version(version_name, version, global_info, ics_config, works)
        suffix = version["info"].get("file", "")
        filename = f"{ics_config['file']}{suffix}.ics"
        (out / filename).write_text(content, encoding="utf-8")
        print(f"已生成 {out / filename}")


if __name__ == "__main__":
    main()
