# bgm API 角色数据抓取。import 或单独运行。
# 单独运行: python scripts/lib/bangumi.py <character_id>

import json
import sys
import time

import requests

UA = "vCal-ACGbday/1.0 (data check; github.com/Vanadiry)"
API = "https://api.bgm.tv/v0/characters/{cid}"
MAX_RETRY = 3


def fetch(cid):  # 返回 {found, birth:{year,month,day}, name, detail}
    result = {"found": False, "birth": None, "name": None, "detail": None}
    for attempt in range(MAX_RETRY):
        try:
            r = requests.get(
                API.format(cid=cid),
                timeout=15,
                headers={"User-Agent": UA},
            )
            if r.status_code == 200:
                d = r.json()
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
            if r.status_code == 404:
                result["detail"] = "404 不存在"
                return result
            # 429/5xx 限速，重试
            result["detail"] = f"HTTP {r.status_code}"
        except requests.RequestException as e:
            result["detail"] = f"请求异常 {e}"
        if attempt < MAX_RETRY - 1:
            time.sleep(2 * (attempt + 1))
    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python scripts/lib/bangumi.py <character_id>")
        sys.exit(2)
    try:
        cid = int(sys.argv[1])
    except ValueError:
        print("character_id 应为整数")
        sys.exit(2)
    print(json.dumps(fetch(cid), ensure_ascii=False))
