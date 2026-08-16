# 构建入口：根据 config.yml 生成 ICS 文件

import argparse
import re
import sys
import uuid as uuid_mod
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "check"))
from check.lint import run_lint

from .config import load_config
from .ics import build_character_event, build_header, build_update_event
from .loader import load_data


def read_existing_dtstamps(path):
    """读取已有 ICS 的 UID -> DTSTAMP 映射。"""
    mapping = {}
    if not path.exists():
        return mapping
    content = path.read_text(encoding="utf-8")
    for m in re.finditer(r"BEGIN:VEVENT\n(.*?)\nEND:VEVENT", content, re.S):
        block = m.group(1)
        uid = re.search(r"UID:(.+)", block)
        stamp = re.search(r"DTSTAMP;VALUE=DATE:(\d{8})", block)
        if uid and stamp:
            mapping[uid.group(1)] = stamp.group(1)
    return mapping


def main():
    parser = argparse.ArgumentParser(description="构建 ICS 文件")
    parser.add_argument("--config", default="config.yml")
    parser.add_argument("--data", default="data")
    parser.add_argument("--output", default="dist")
    args = parser.parse_args()

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

    now = datetime.now()
    build_meta = {
        "version": f"{now.year}.{now.month:02d}{now.day:02d}.{now.hour:02d}{now.minute:02d}{now.second:02d}",
        "uuid": str(uuid_mod.uuid4()),
        "dtstamp": now.strftime("%Y%m%d"),
        "update_dtstart": now.year - 1,
        "summary": global_info["name"],
    }

    for version in config["ics"].values():
        suffix = version["info"].get("file", "")
        filename = f"{ics_config['file']}{suffix}.ics"
        out_path = out / filename
        old_dtstamps = read_existing_dtstamps(out_path)

        events = []
        for work in works:
            info = work["info"]
            for character in work["characters"]:
                dtstamp = old_dtstamps.get(character.get("uuid"))
                ev = build_character_event(
                    character,
                    info,
                    version,
                    ics_config,
                    dtstamp=dtstamp or build_meta["dtstamp"],
                )
                if ev:
                    events.append(ev)

        header = build_header(global_info, version["info"], ics_config)
        update = build_update_event(global_info, ics_config, version["info"]["name"], build_meta)
        content = "\n\n".join([header, update, *events]) + "\nEND:VCALENDAR"
        out_path.write_text(content, encoding="utf-8")
        print(f"已生成 {out_path}")


if __name__ == "__main__":
    main()
