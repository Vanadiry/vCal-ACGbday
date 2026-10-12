# 报告写入：列表段逐条追加，避免长任务中反复全量重写（每次重写都要重新序列化累积内容，开销 O(n²)）
#
# 结构为「头部字段 + 若干列表段 + summary」。
# summary 必须最后写——追加只能向后写，已落盘的键无法回头修改。

import textwrap
from datetime import datetime
from pathlib import Path

import yaml


class Report:
    """YAML 报告。构造时截断文件并写入头部，列表段用 add 追加，finish 收尾写 summary。"""

    def __init__(self, path, **header):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        body = {"generated": datetime.now().isoformat(timespec="seconds"), **header}
        self._f = self.path.open("w", encoding="utf-8")
        self._f.write(
            yaml.safe_dump(body, allow_unicode=True, sort_keys=False, default_flow_style=False)
        )
        self._section = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def add(self, key, item):  # 向列表段追加一条，首次追加时写出段名
        if self._section != key:
            self._f.write(f"{key}:\n")
            self._section = key
        frag = yaml.safe_dump(
            [item], allow_unicode=True, sort_keys=False, default_flow_style=False
        )
        self._f.write(textwrap.indent(frag, "  "))
        self._f.flush()  # 长任务中途查看报告时能读到已追加的内容

    def finish(self, **summary):  # 收尾写 summary，必须在所有 add 之后调用
        self._f.write(
            yaml.safe_dump(
                {"summary": summary}, allow_unicode=True, sort_keys=False, default_flow_style=False
            )
        )

    def close(self):
        if self._f is not None:
            self._f.close()
            self._f = None
