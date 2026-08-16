# 萌娘百科页面抓取，提取生日。import 或单独运行。
# 单独运行: python scripts/lib/moegirl.py <条目名>

import html
import json
import re
import sys
import time
from urllib.parse import quote

import requests

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
BASE = "https://zh.moegirl.org.cn/{name}"
MAX_RETRY = 3
RETRY_WAIT = 5

# div 结构: <span>生日</span></div><div> 值 </div>
DIV_PAT = re.compile(
    r'font-weight: bold; text-align: center;"><span>([^<]+)</span></div>'
    r"<div[^>]*>(.*?)</div>",
    re.S,
)
# td 表格结构: <td>生日</td> <td> 值 </td>
TD_PAT = re.compile(r"<td[^>]*>\s*生日\s*</td>\s*<td[^>]*>(.*?)</td>", re.S)
# 年份可选: 1966年11月1日 / 11月1日
BDAY_PAT = re.compile(r"(?:(\d{4})\s*年)?\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日")


def _extract_birth(text):
    for pat in (DIV_PAT, TD_PAT):
        for m in pat.finditer(text):
            if pat is TD_PAT:
                val = m.group(1)
            else:
                if html.unescape(m.group(1)).strip() != "生日":
                    continue
                val = m.group(2)
            val = html.unescape(re.sub(r"<[^>]+>", "", val)).strip()
            bm = BDAY_PAT.search(val)
            if bm:
                year = int(bm.group(1)) if bm.group(1) else None
                return {"year": year, "month": int(bm.group(2)), "day": int(bm.group(3))}
    return None


def fetch(name):  # 返回 {found, birth:{year,month,day}, name, detail}
    result = {"found": False, "birth": None, "name": None, "detail": None}
    url = BASE.format(name=quote(name))
    for attempt in range(MAX_RETRY):
        try:
            r = requests.get(url, timeout=20, headers={"User-Agent": UA})
            if r.status_code == 403:
                result["detail"] = f"403 限速 (第{attempt + 1}次)"
                if attempt < MAX_RETRY - 1:
                    time.sleep(RETRY_WAIT)
                    continue
                return result
            if r.status_code == 404:
                result["detail"] = "404 页面不存在"
                return result
            if r.status_code != 200:
                result["detail"] = f"HTTP {r.status_code}"
                return result
            aid = re.search(r'"wgArticleId":(\d+)', r.text)
            if aid and aid.group(1) == "0":
                result["detail"] = "页面不存在"
                return result
            birth = _extract_birth(r.text)
            result["found"] = True
            result["name"] = name
            result["birth"] = birth
            result["detail"] = "无生日字段" if birth is None else None
            return result
        except requests.RequestException as e:
            result["detail"] = f"请求异常 {e}"
            if attempt < MAX_RETRY - 1:
                time.sleep(2)
    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python scripts/lib/moegirl.py <条目名>")
        sys.exit(2)
    print(json.dumps(fetch(sys.argv[1]), ensure_ascii=False))
