# bgm API 角色数据抓取。import 或单独运行。
# 单独运行: python scripts/lib/bangumi.py <character_id>

import argparse
import json
import time

import requests

UA = "Vanadiry/vCal-ACGbday (https://github.com/Vanadiry/vCal-ACGbday)"
BASE = "https://api.bgm.tv/v0"
MAX_RETRY = 3
TOKEN = None


def set_token(token):
    """设置 bangumi 访问令牌。传入 None/空串 则清除（恢复匿名请求）。"""
    global TOKEN
    TOKEN = (token or "").strip() or None


def _get(path):
    headers = {"User-Agent": UA}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    for attempt in range(MAX_RETRY):
        try:
            r = requests.get(f"{BASE}{path}", timeout=15, headers=headers)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 404:
                return None
            if r.status_code == 403:
                return {"rate_limited": True}
        except requests.RequestException as e:
            return {"error": str(e)}
        if attempt < MAX_RETRY - 1:
            time.sleep(2 * (attempt + 1))
    return None


def fetch_subject(sid):
    """拉取 subject 主数据。返回 {name, name_cn, ...}"""
    return _get(f"/subjects/{sid}")


def fetch_subject_characters(sid):
    """拉取 subject 的角色列表。返回 [{id, name, relation}]"""
    data = _get(f"/subjects/{sid}/characters")
    if not data:
        return []
    return data


def fetch_character(cid):
    """拉取角色详情。返回完整数据 dict 或 None"""
    return _get(f"/characters/{cid}")


def fetch(cid):  # 返回 {found, birth:{year,month,day}, name, detail}
    result = {"found": False, "birth": None, "name": None, "detail": None}
    d = fetch_character(cid)
    if d is None:
        result["detail"] = "404 不存在"
        return result
    if isinstance(d, dict) and "error" in d:
        result["detail"] = f"请求异常 {d['error']}"
        return result
    birth = {
        "year": d.get("birth_year"),
        "month": d.get("birth_mon"),
        "day": d.get("birth_day"),
    }
    if not any(v is not None for v in birth.values()):
        result["detail"] = "无生日数据"
    else:
        result["birth"] = birth
    result["found"] = True
    result["name"] = d.get("name")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="抓取 bgm 角色数据")
    parser.add_argument("character_id", type=int, help="角色 id")
    parser.add_argument("--auth", default=None, help="bangumi 访问令牌，用于拉取受限条目")
    args = parser.parse_args()
    set_token(args.auth)
    print(json.dumps(fetch(args.character_id), ensure_ascii=False))
