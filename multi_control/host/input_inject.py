"""远程输入注入 — PostMessage 实现独立光标，不影响被控端系统光标。"""

import ctypes
from ctypes import wintypes

import win32api
import win32con
import win32gui

# ── 键盘 SendInput ──────────────────────────
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class INPUT_UNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("union", INPUT_UNION)]


user32 = ctypes.windll.user32


def _send_keyboard(vk: int, pressed: bool) -> None:
    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.union.ki.wVk = vk
    inp.union.ki.wScan = 0
    inp.union.ki.dwFlags = 0 if pressed else KEYEVENTF_KEYUP
    arr = (INPUT * 1)(inp)
    result = user32.SendInput(1, arr, ctypes.sizeof(INPUT))
    if result == 0:
        err = ctypes.windll.kernel32.GetLastError()
        print(f"SendInput(key) failed: error={err}")


# ── 公共 API ────────────────────────────────


def inject_mouse_move(x: int, y: int, screen_w: int, screen_h: int) -> None:
    """仅存根，不移动系统光标。光标由 overlay 单独管理。"""
    pass


def inject_mouse_button(button: str, pressed: bool, x: int, y: int) -> None:
    """PostMessage 发送按键事件到 (x,y) 下方的窗口，不碰系统光标。"""
    hwnd = win32gui.WindowFromPoint((x, y))
    if not hwnd:
        return

    msg_map = {
        ("left", True): win32con.WM_LBUTTONDOWN,
        ("left", False): win32con.WM_LBUTTONUP,
        ("right", True): win32con.WM_RBUTTONDOWN,
        ("right", False): win32con.WM_RBUTTONUP,
        ("middle", True): win32con.WM_MBUTTONDOWN,
        ("middle", False): win32con.WM_MBUTTONUP,
    }
    msg = msg_map.get((button, pressed))
    if msg is None:
        return

    cx, cy = win32gui.ScreenToClient(hwnd, (x, y))
    lparam = win32api.MAKELONG(cx, cy)
    wparam = 0
    if pressed:
        btn_id = {"left": win32con.MK_LBUTTON, "right": win32con.MK_RBUTTON, "middle": win32con.MK_MBUTTON}
        wparam = btn_id.get(button, 0)
    win32gui.PostMessage(hwnd, msg, wparam, lparam)


def inject_mouse_wheel(delta: int, x: int, y: int) -> None:
    """PostMessage 发送滚轮事件到 (x,y) 下方的窗口。"""
    hwnd = win32gui.WindowFromPoint((x, y))
    if not hwnd:
        return

    cx, cy = win32gui.ScreenToClient(hwnd, (x, y))
    wparam = win32api.MAKELONG(0, delta * 120)
    lparam = win32api.MAKELONG(cx, cy)
    win32gui.PostMessage(hwnd, win32con.WM_MOUSEWHEEL, wparam, lparam)


def inject_key(vk: int, pressed: bool) -> None:
    """按下/释放键盘按键，vk 为 Windows 虚拟键码。"""
    _send_keyboard(vk, pressed)
