# 构建入口：根据 config.yml 生成 ICS 文件

import argparse
import re
import sys
import uuid as uuid_mod
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.check.dist_ics import check_dist
from scripts.check.lint import run_lint

from .config import load_config
from .ics import build_character_event, build_header, build_update_event
from .js import build_js
from .list import build_list
from .loader import load_data


def normalize_event(block):
    """剔除 DTSTAMP 与 BEGIN/END:VEVENT，得到事件的实际内容。

    比对两侧必须走同一个函数，否则格式差异会被误判为内容变化。
    """
    lines = block.split("\n")
    return "\n".join(
        line
        for line in lines
        if line not in ("BEGIN:VEVENT", "END:VEVENT") and not line.startswith("DTSTAMP")
    )


def read_existing_events(path):
    """读取已有 ICS，返回 UID -> (DTSTAMP, 事件内容, 原始内容)。"""
    mapping = {}
    if not path.exists():
        return mapping
    content = path.read_text(encoding="utf-8")
    for m in re.finditer(r"BEGIN:VEVENT\n(.*?)\nEND:VEVENT", content, re.S):
        block = m.group(1)
        uid = re.search(r"^UID:(.+)$", block, re.M)
        # 兼容迁移前的 VALUE=DATE 写法
        stamp = re.search(r"^DTSTAMP(?:;VALUE=DATE)?:(\d{8}(?:T\d{6}Z)?)$", block, re.M)
        if uid and stamp:
            mapping[uid.group(1)] = (stamp.group(1), normalize_event(block), block)
    return mapping


def report(path, content):
    """写入产物。内容与已有文件相同时不重写，并如实告知。"""
    if path.exists() and path.read_text(encoding="utf-8") == content:
        print(f"无变化 {path}")
        return
    path.write_text(content, encoding="utf-8")
    print(f"已生成 {path}")


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
    global_config = config["global"]
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    now = datetime.now()
    build_meta = {
        "version": f"{now.year}.{now.month:02d}{now.day:02d}.{now.hour:02d}{now.minute:02d}{now.second:02d}",
        # 固定 UUID，使各版本的 update 事件原地更新而非每次新增
        "uuid": str(uuid_mod.uuid5(uuid_mod.NAMESPACE_URL, f"vcal-update-{ics_config['file']}")),
        "dtstamp": now.strftime("%Y%m%dT%H%M%SZ"),
        "update_dtstart": now.year - 1,
        "summary": global_info["name"],
    }

    for version in config["ics"].values():
        suffix = version["info"].get("file", "")
        filename = f"{ics_config['file']}{suffix}.ics"
        out_path = out / filename
        old_events = read_existing_events(out_path)

        events = []
        changed = False
        for work in works:
            info = work["info"]
            for character in work["characters"]:
                ev = build_character_event(
                    character,
                    info,
                    version,
                    ics_config,
                    dtstamp=build_meta["dtstamp"],
                )
                if ev is None:
                    continue
                # 内容与上次构建一致则沿用旧 DTSTAMP，客户端据此忽略更新
                uid = character["uuid"]
                old = old_events.get(uid)
                if old and normalize_event(ev) == old[1]:
                    ev = ev.replace(f"DTSTAMP:{build_meta['dtstamp']}", f"DTSTAMP:{old[0]}", 1)
                else:
                    changed = True
                events.append(ev)

        header = build_header(global_info, version["info"], ics_config)
        old_update = old_events.get(build_meta["uuid"])
        if changed or old_update is None:
            update = build_update_event(
                global_info, ics_config, version["info"]["name"], build_meta
            )
        else:
            # 无任何条目变化时不发新版本号，原样沿用上次构建的 update 事件
            update = f"BEGIN:VEVENT\n{old_update[2]}\nEND:VEVENT"
        content = "\n\n".join([header, update, *events]) + "\nEND:VCALENDAR"
        report(out_path, content)

    report(out / "list.md", build_list(works))

    for version_name, version in config.get("js", {}).items():
        content = build_js(works, version, version_name, global_info, global_config)
        suffix = version.get("file", "")
        filename = f"{ics_config['file']}{suffix}.js"
        report(out / filename, content)

    dist_errs = check_dist(args.output)
    if dist_errs != 0:
        print("\n产物检查未通过，请修正后重新构建")
        sys.exit(1)


if __name__ == "__main__":
    main()
