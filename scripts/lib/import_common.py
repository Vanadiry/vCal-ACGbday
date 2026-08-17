# import 共用：并发控制、YAML 输出、名字解析、角色数据生成

import threading
import time
import uuid as uuid_mod

import yaml

from lib.status import status_mark

CONCURRENCY = 12
STOP_PAUSE = 30


class StopOnRateLimit(Exception):
    pass


class RateController:
    def __init__(self, start_concurrency=CONCURRENCY):
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
        with self.lock:
            self.sem = threading.Semaphore(self.concurrency)


def guarded_get(controller, fetch_fn, *args):
    while True:
        controller.acquire()
        try:
            result = fetch_fn(*args)
        finally:
            controller.release()
        if isinstance(result, dict) and result.get("rate_limited"):
            if not controller.handle_rate_limit():
                raise StopOnRateLimit()
            continue
        return result


class BlockDumper(yaml.SafeDumper):
    pass


def str_rep(dumper, data):
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


BlockDumper.add_representer(str, str_rep)


def _strip(s):
    return str(s).replace(" ", "").replace("　", "") if s else ""


def clean_main(summary):
    main = summary.replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(line.rstrip() for line in main.split("\n")).strip()


def get_cn_name(detail):
    for item in detail.get("infobox", []) or []:
        if item.get("key") == "简体中文名":
            return item.get("value")
    return None


def get_aliases(detail):
    """返回别名列表：[(k, v)]，k 可能为 None"""
    result = []
    for item in detail.get("infobox", []) or []:
        if item.get("key") != "别名":
            continue
        for alias in item.get("value", []) or []:
            if isinstance(alias, dict):
                result.append((alias.get("k"), alias.get("v")))
    return result


def get_name(detail, key):
    for k, v in get_aliases(detail):
        if k == key:
            return v
    return None


def make_character(detail, null_fill=False):
    """生成角色数据。

    null_fill=True（tracker 模式）时，解析不到的内容用 null 占位，
    让 lint 报错以提醒补充；desc.main 缺省时为两行 null。
    """
    orig = detail.get("name") or ""
    name = {"orig": orig}
    cn = get_cn_name(detail)
    if cn:
        name["zh"] = _strip(cn)
    elif null_fill:
        name["zh"] = 0
    jp_name = get_name(detail, "日文名")
    name["ja"] = jp_name if jp_name else None
    kana = get_name(detail, "纯假名")
    if kana:
        name["ja-kana"] = kana
    elif null_fill:
        name["ja-kana"] = None

    # 注释记录其他名字
    comments = []
    if jp_name and jp_name != orig:
        comments.append(f"日文名: {jp_name}")
    roman = get_name(detail, "罗马字")
    if roman:
        comments.append(f"罗马字: {roman}")
    second_cn = get_name(detail, "第二中文名")
    if second_cn:
        comments.append(f"第二中文名: {second_cn}")
    for k, v in get_aliases(detail):
        if k is None and v:
            comments.append(f"别名: {v}")
    if not jp_name:
        comments.append("待补充日文名")
    if not kana:
        comments.append("待补充假名")

    char = {"name": name}
    birth_mon, birth_day = detail.get("birth_mon"), detail.get("birth_day")
    if null_fill:
        char["bday"] = {
            "m": birth_mon,
            "d": birth_day,
            "y": detail.get("birth_year"),
        }
    elif birth_mon and birth_day:
        bday = {"m": birth_mon, "d": birth_day}
        if detail.get("birth_year"):
            bday["y"] = detail["birth_year"]
        char["bday"] = bday
    summary = detail.get("summary")
    if summary:
        char["desc"] = {"main": clean_main(summary)}
    elif null_fill:
        char["desc"] = {"main": "null\nnull"}
    char["uuid"] = str(uuid_mod.uuid4())
    char["refs"] = {"bangumi": detail["id"]}
    char["_comments"] = comments
    return char
