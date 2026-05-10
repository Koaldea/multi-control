"""通过 SendInput API 注入远程键鼠事件到 Windows 输入队列."""

import ctypes
from ctypes import wintypes

# Win32 常量
INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_WHEEL = 0x0800
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
    ]


class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("union", INPUT_UNION),
    ]


user32 = ctypes.windll.user32


def _send_input(*inputs: INPUT) -> int:
    arr = (INPUT * len(inputs))(*inputs)
    result = user32.SendInput(len(arr), arr, ctypes.sizeof(INPUT))
    if result == 0:
        err = ctypes.windll.kernel32.GetLastError()
        print(f"SendInput failed: error={err}")
    return result


def inject_mouse_move(x: int, y: int, screen_w: int, screen_h: int) -> None:
    """移动鼠标到绝对坐标 (x, y)，坐标范围 0-screen_w, 0-screen_h."""
    abs_x = int(x * 65535 / (screen_w - 1)) if screen_w > 1 else 0
    abs_y = int(y * 65535 / (screen_h - 1)) if screen_h > 1 else 0

    inp = INPUT()
    inp.type = INPUT_MOUSE
    inp.union.mi.dx = abs_x
    inp.union.mi.dy = abs_y
    inp.union.mi.mouseData = 0
    inp.union.mi.dwFlags = MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE
    _send_input(inp)


def inject_mouse_button(button: str, pressed: bool) -> None:
    """按下/释放鼠标按键. button: 'left' | 'right' | 'middle'."""
    flags = {
        ("left", True): MOUSEEVENTF_LEFTDOWN,
        ("left", False): MOUSEEVENTF_LEFTUP,
        ("right", True): MOUSEEVENTF_RIGHTDOWN,
        ("right", False): MOUSEEVENTF_RIGHTUP,
        ("middle", True): MOUSEEVENTF_MIDDLEDOWN,
        ("middle", False): MOUSEEVENTF_MIDDLEUP,
    }
    flag = flags.get((button, pressed))
    if flag is None:
        return

    inp = INPUT()
    inp.type = INPUT_MOUSE
    inp.union.mi.dwFlags = flag
    _send_input(inp)


def inject_mouse_wheel(delta: int) -> None:
    """滚轮滚动，delta 正=上滚，负=下滚."""
    inp = INPUT()
    inp.type = INPUT_MOUSE
    inp.union.mi.mouseData = delta * 120
    inp.union.mi.dwFlags = MOUSEEVENTF_WHEEL
    _send_input(inp)


def inject_key(vk: int, pressed: bool) -> None:
    """按下/释放键盘按键，vk 为 Windows 虚拟键码."""
    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.union.ki.wVk = vk
    inp.union.ki.wScan = 0
    inp.union.ki.dwFlags = KEYEVENTF_KEYUP if not pressed else 0
    _send_input(inp)
