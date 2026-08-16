# 补全已有数据：遍历 data/ 的 _info.yaml，从 bangumi 拉取缺失角色
# 有生日 → 建 import/<作品名>/<角色>.yml；无生日 → 记录 import/report.yml

import argparse
import sys
import threading
import time
import uuid as uuid_mod
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from lib import bangumi
from lib.color import info
from lib.status import status_mark

CONCURRENCY = 12
STOP_PAUSE = 30


class RateController:
    def __init__(self, start_concurrency):
        self.concurrency = start_concurrency
        self.sem = threading.Semaphore(start_concurrency)
        self.rate_hits = 0
        self.lock = threading.Lock()

    def acquire(self):
        self.sem.acquire()

    def release(self):
        self.sem.release()

    def handle_rate_limit(self):
        with self.lock:
            self.rate_hits += 1
            hit = self.rate_hits
            if hit == 1:
                self.concurrency = 8
            elif hit == 2:
                self.concurrency = 4
            else:
                return False
        print(
            f"  {status_mark('X')} 检测到 403 限速，并发降至 {self.concurrency}，静置 {STOP_PAUSE}s",
            flush=True,
        )
        time.sleep(STOP_PAUSE)
        self._reset_sem()
        return True

    def _reset_sem(self):
        new = threading.Semaphore(self.concurrency)
        with self.lock:
            self.sem = new


class BlockDumper(yaml.SafeDumper):
    pass


def str_rep(dumper, data):
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


BlockDumper.add_representer(str, str_rep)


def _strip(s):
    return str(s).replace(" ", "").replace("　", "") if s else ""


def load_works(data_dir):
    works = []
    for folder in sorted(Path(data_dir).iterdir()):
        if not folder.is_dir():
            continue
        info_file = folder / "_info.yaml"
        if not info_file.exists():
            continue
        with open(info_file, encoding="utf-8") as f:
            info = yaml.safe_load(f)
        existing = set()
        for p in folder.glob("*.yml"):
            if p.name == "_info.yaml":
                continue
            d = yaml.safe_load(p.read_text(encoding="utf-8"))
            bid = (d.get("refs") or {}).get("bangumi")
            if bid:
                existing.add(int(bid))
        works.append({"folder": folder.name, "info": info, "existing": existing})
    return works


def get_cn_name(detail):
    for item in detail.get("infobox", []) or []:
        if item.get("key") == "简体中文名":
            return item.get("value")
    return None


def make_character(detail):
    name = {"orig": detail.get("name") or ""}
    cn = get_cn_name(detail)
    if cn:
        name["zh"] = cn
    char = {"name": name, "uuid": str(uuid_mod.uuid4())}
    birth_mon, birth_day = detail.get("birth_mon"), detail.get("birth_day")
    if birth_mon and birth_day:
        bday = {"m": birth_mon, "d": birth_day}
        if detail.get("birth_year"):
            bday["y"] = detail["birth_year"]
        char["bday"] = bday
    if detail.get("summary"):
        char["desc"] = {"main": detail["summary"]}
    char["refs"] = {"bangumi": detail["id"]}
    return char


def main():
    parser = argparse.ArgumentParser(description="从 bangumi 补全缺失角色")
    parser.add_argument("--data", default="data", help="数据目录")
    parser.add_argument("--import-dir", default="import", help="import 输出目录")
    parser.add_argument("--report", default="import/report.yml", help="报告路径")
    parser.add_argument("--no-color", action="store_true")
    args = parser.parse_args()

    if args.no_color:
        import os

        os.environ["NO_COLOR"] = "1"

    works = load_works(args.data)
    print(info(f"扫描: {len(works)} 部作品"))

    import_dir = Path(args.import_dir)
    import_dir.mkdir(parents=True, exist_ok=True)

    report = {
        "generated": datetime.now().isoformat(timespec="seconds"),
        "items": [],
    }
    items_lock = threading.Lock()

    counts = {"新增": 0, "已有": 0, "客串": 0, "无生日": 0, "失败": 0}
    counts_lock = threading.Lock()

    def log(work, name, mark, kind):
        with counts_lock:
            counts[kind] += 1
        print(f"  {status_mark(mark)} {work['folder']}/{name} [{kind}]", flush=True)

    controller = RateController(CONCURRENCY)

    class StopOnRateLimit(Exception):
        pass

    def guarded_get(fetch_fn, *args):
        while True:
            controller.acquire()
            try:
                result = fetch_fn(*args)
            finally:
                controller.release()
            if isinstance(result, dict) and result.get("rate_limited"):
                ok = controller.handle_rate_limit()
                if not ok:
                    raise StopOnRateLimit()
                continue
            return result

    def process_character(work, sid, c):
        cid = c.get("id")
        name = c.get("name") or cid
        if not cid:
            return
        if cid in work["existing"]:
            log(work, name, "Y", "已有")
            return
        if c.get("relation") == "客串":
            log(work, name, "Y", "客串")
            return
        detail = guarded_get(bangumi.fetch_character, cid)
        if not detail or isinstance(detail, dict) and "error" in detail:
            with items_lock:
                report["items"].append(
                    {
                        "work": work["folder"],
                        "subject_id": sid,
                        "character": name,
                        "character_id": cid,
                        "reason": "详情获取失败",
                    }
                )
            log(work, name, "X", "失败")
            return
        birth_mon, birth_day = detail.get("birth_mon"), detail.get("birth_day")
        if not birth_mon or not birth_day:
            with items_lock:
                report["items"].append(
                    {
                        "work": work["folder"],
                        "subject_id": sid,
                        "character": name,
                        "character_id": cid,
                        "reason": "无生日数据",
                    }
                )
            log(work, name, "?", "无生日")
            return
        char = make_character(detail)
        out_dir = import_dir / work["folder"]
        out_dir.mkdir(parents=True, exist_ok=True)
        filename = _strip(char["name"].get("zh") or char["name"]["orig"])
        out = out_dir / f"{filename}.yml"
        out.write_text(
            yaml.dump(
                char,
                Dumper=BlockDumper,
                allow_unicode=True,
                sort_keys=False,
                default_flow_style=False,
            ),
            encoding="utf-8",
        )
        log(work, name, "Y", "新增")

    def process_subject(work, sid):
        chars = guarded_get(bangumi.fetch_subject_characters, sid)
        print(
            f"  {status_mark('Y')} {work['folder']} (subject {sid}) 拉取完成: {len(chars)} 角色",
            flush=True,
        )
        return [(work, sid, c) for c in chars]

    subjects = []
    for work in works:
        subject_ids = (work["info"].get("id") or {}).get("bangumi") or []
        for sid in subject_ids:
            subjects.append((work, sid))

    # 阶段 1：12 并发拉取 subject 角色列表
    char_tasks = []
    try:
        with ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
            for tasks in pool.map(lambda t: process_subject(*t), subjects):
                char_tasks.extend(tasks)
    except StopOnRateLimit:
        print(f"\n{info('连续 403，任务停止')}")
        sys.exit(1)
    print(info(f"\n阶段 1 完成，共 {len(char_tasks)} 个角色待处理"))

    # 阶段 2：12 并发处理角色详情
    try:
        with ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
            pool.map(lambda t: process_character(*t), char_tasks)
    except StopOnRateLimit:
        print(f"\n{info('连续 403，任务停止')}")
        sys.exit(1)

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        yaml.safe_dump(report, allow_unicode=True, sort_keys=False, default_flow_style=False),
        encoding="utf-8",
    )
    summary = "  ".join(f"{k}: {v}" for k, v in counts.items())
    print(f"\n{info('汇总')} {summary}")
    print(f"{info(f'报告已写入: {report_path}')} ({len(report['items'])} 条无生日/失败)")


if __name__ == "__main__":
    main()
