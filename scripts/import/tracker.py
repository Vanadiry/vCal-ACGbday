# 从 tracker.yml 拉取整部作品：生成 import/<folder>/_info.yml 与角色 yml
# 解析不到的内容用 null 占位，让 lint 报错以提醒补充

import argparse
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from lib import bangumi
from lib.color import info
from lib.import_common import (
    CONCURRENCY,
    BlockDumper,
    RateController,
    StopOnRateLimit,
    _strip,
    guarded_get,
    make_character,
)
from lib.status import status_mark


def load_tracker(path):
    items = yaml.safe_load(path.read_text(encoding="utf-8"))
    works = []
    for item in items or []:
        name = item.get("name")
        subjects = item.get("subject") or []
        if not name or not subjects:
            continue
        works.append({"folder": name, "subject": [int(s) for s in subjects]})
    return works


def write_yml(path, data, comments=None):
    body = yaml.dump(
        data,
        Dumper=BlockDumper,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    )
    if comments:
        comment_text = "\n".join(f"# {c}" for c in comments)
        body = comment_text + "\n" + body
    path.write_text(body, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="从 tracker.yml 拉取整部作品数据")
    parser.add_argument("--tracker", default="import/tracker.yml", help="tracker 文件路径")
    parser.add_argument("--import-dir", default="import", help="import 输出目录")
    parser.add_argument("--auth", default=None, help="bangumi 访问令牌，用于拉取受限条目")
    parser.add_argument("--no-color", action="store_true")
    args = parser.parse_args()

    if args.auth:
        bangumi.set_token(args.auth)

    if args.no_color:
        import os

        os.environ["NO_COLOR"] = "1"

    tracker_path = Path(args.tracker)
    if not tracker_path.exists():
        print(f"{info('tracker 不存在')}: {tracker_path}")
        sys.exit(1)
    works = load_tracker(tracker_path)
    if not works:
        print("tracker 无有效条目")
        sys.exit(1)
    print(info(f"tracker: {len(works)} 部作品"))

    import_dir = Path(args.import_dir)
    import_dir.mkdir(parents=True, exist_ok=True)
    controller = RateController()

    counts = {"角色": 0, "失败": 0}
    counts_lock = threading.Lock()

    def log(folder, name, mark, kind):
        with counts_lock:
            counts[kind] += 1
        print(f"  {status_mark(mark)} {folder}/{name} [{kind}]", flush=True)

    # 阶段 1：拉取 subject 主数据，合并生成各作品的 _info.yml
    try:
        with ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
            futures = []
            for work in works:
                for sid in work["subject"]:
                    futures.append(
                        (
                            work,
                            sid,
                            pool.submit(guarded_get, controller, bangumi.fetch_subject, sid),
                        )
                    )
            subject_info = {sid: f.result() for work, sid, f in futures}
    except StopOnRateLimit:
        print(f"\n{info('连续 403，任务停止')}")
        sys.exit(1)

    for work in works:
        folder = import_dir / work["folder"]
        folder.mkdir(parents=True, exist_ok=True)
        first = None
        for sid in work["subject"]:
            d = subject_info.get(sid)
            if isinstance(d, dict) and d.get("error"):
                print(f"  {status_mark('X')} {work['folder']} subject {sid} 拉取失败")
                continue
            if first is None and d:
                first = d
        if first:
            name = {"orig": first.get("name") or str(work["subject"][0])}
            cn = first.get("name_cn")
            name["zh"] = _strip(cn) if cn else 0
            write_yml(
                folder / "_info.yml",
                {"name": name, "id": {"bangumi": work["subject"]}},
            )
        print(f"  {status_mark('Y')} {work['folder']} subject 拉取完成", flush=True)

    # 阶段 2：拉取 subject 角色列表
    char_tasks = []
    try:
        with ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
            futures = []
            for work in works:
                for sid in work["subject"]:
                    futures.append(
                        (
                            work,
                            sid,
                            pool.submit(
                                guarded_get, controller, bangumi.fetch_subject_characters, sid
                            ),
                        )
                    )
            for work, sid, f in futures:
                chars = f.result()
                if not chars or isinstance(chars, dict):
                    continue
                for c in chars:
                    char_tasks.append((work, sid, c))
    except StopOnRateLimit:
        print(f"\n{info('连续 403，任务停止')}")
        sys.exit(1)
    print(info(f"\n阶段 2 完成，共 {len(char_tasks)} 个角色待处理"))

    # 阶段 3：拉取角色详情，生成角色 yml
    def process_character(work, sid, c):
        cid = c.get("id")
        name = c.get("name") or cid
        if not cid:
            return
        if c.get("relation") == "客串":
            return
        detail = guarded_get(controller, bangumi.fetch_character, cid)
        if not detail or isinstance(detail, dict) and "error" in detail:
            log(work["folder"], name, "X", "失败")
            return
        char = make_character(detail, null_fill=True)
        comments = char.pop("_comments", [])
        out_dir = import_dir / work["folder"]
        out_dir.mkdir(parents=True, exist_ok=True)
        filename = _strip(char["name"].get("zh") or char["name"]["orig"])
        if not filename or filename == "0":
            filename = str(cid)
        write_yml(out_dir / f"{filename}.yml", char, comments)
        log(work["folder"], name, "Y", "角色")

    try:
        with ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
            pool.map(lambda t: process_character(*t), char_tasks)
    except StopOnRateLimit:
        print(f"\n{info('连续 403，任务停止')}")
        sys.exit(1)

    summary = "  ".join(f"{k}: {v}" for k, v in counts.items())
    print(f"\n{info('汇总')} {summary}")


if __name__ == "__main__":
    main()
