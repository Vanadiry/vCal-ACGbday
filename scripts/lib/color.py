# 终端彩色输出支持。import 或单独运行打印颜色示例。

import os
import sys

# ANSI 颜色码
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[37m"
BG_RED = "\033[41m"
BG_GREEN = "\033[42m"
BG_YELLOW = "\033[43m"
BG_BLUE = "\033[44m"
BG_MAGENTA = "\033[45m"
BG_CYAN = "\033[46m"

# 关闭颜色（非 tty 或 NO_COLOR 环境变量时）
_USE_COLOR = sys.stdout.isatty() and not os.environ.get("NO_COLOR")


def color(text, *codes):  # 给文本加颜色
    if not _USE_COLOR:
        return text
    code_str = "".join(codes)
    return f"{code_str}{text}{RESET}"


def cprint(text="", *codes, **kwargs):  # 带颜色打印
    end = kwargs.pop("end", "\n")
    file = kwargs.pop("file", sys.stdout)
    print(color(text, *codes), end=end, file=file, **kwargs)


# 语义化便捷函数
def ok(text):
    return color(text, GREEN)


def warn(text):
    return color(text, YELLOW)


def error(text):
    return color(text, RED)


def info(text):
    return color(text, CYAN)


def bold(text):
    return color(text, BOLD)


def dim(text):
    return color(text, DIM)


if __name__ == "__main__":
    print("颜色支持模块测试:")
    print(
        f"  {ok('OK')}  {warn('WARN')}  {error('ERROR')}  {info('INFO')}  {bold('BOLD')}  {dim('DIM')}"
    )
