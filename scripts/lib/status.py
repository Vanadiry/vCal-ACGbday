# 通用状态标记。Y=PASS(绿) X=不符(红) ?=新增(橙)

from color import color

STATUS_Y = color("Y", "\033[32m")
STATUS_X = color("X", "\033[31m")
STATUS_QM = color("?", "\033[33m")


def status_mark(code):  # code: 'Y'/'X'/'?' -> 带颜色的标记
    if code == "Y":
        return STATUS_Y
    if code == "X":
        return STATUS_X
    if code == "?":
        return STATUS_QM
    return code
