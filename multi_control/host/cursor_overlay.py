"""GDI 透明覆盖窗口 — 在被控端屏幕上渲染远程用户的独立光标。"""

import ctypes
import threading

import win32api
import win32con
import win32gui

CURSOR_SIZE = 48

_user32 = ctypes.windll.user32


class CursorOverlay:
    """透明顶层窗口，在被控端绘制第二个光标（远程用户的鼠标位置）。"""

    def __init__(self):
        self._x = 0
        self._y = 0
        self._lock = threading.Lock()
        self._running = False
        self._hwnd = None
        self._hdc_mem = None
        self._bmp = None
        self._old_bmp = None
        self._thread: threading.Thread | None = None

    # ── public API ──────────────────────────────────────────

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._running = True
        self._thread.start()

    def stop(self) -> None:
        self._running = False

    def update(self, x: int, y: int) -> None:
        with self._lock:
            self._x = x
            self._y = y

    # ── window proc ─────────────────────────────────────────

    def _wnd_proc(self, hwnd: int, msg: int, wparam: int, lparam: int) -> int:
        if msg == win32con.WM_TIMER:
            self._redraw()
        elif msg == win32con.WM_DESTROY:
            win32gui.PostQuitMessage(0)
        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    # ── internal ────────────────────────────────────────────

    def _run(self) -> None:
        module = win32api.GetModuleHandle(None)

        wc = win32gui.WNDCLASS()
        wc.lpfnWndProc = self._wnd_proc
        wc.hInstance = module
        wc.lpszClassName = "MCCursorOverlay"
        wc.hbrBackground = win32gui.GetStockObject(win32con.NULL_BRUSH)

        atom = win32gui.RegisterClass(wc)

        ex_style = (
            win32con.WS_EX_LAYERED
            | win32con.WS_EX_TRANSPARENT
            | win32con.WS_EX_TOPMOST
            | win32con.WS_EX_TOOLWINDOW
            | win32con.WS_EX_NOACTIVATE
        )

        self._hwnd = win32gui.CreateWindowEx(
            ex_style,
            atom,
            "MC Cursor",
            win32con.WS_POPUP,
            0, 0, CURSOR_SIZE, CURSOR_SIZE,
            None, None, module, None,
        )

        # 黑色 = 透明色
        win32gui.SetLayeredWindowAttributes(
            self._hwnd, win32api.RGB(0, 0, 0), 0, win32con.LWA_COLORKEY
        )

        self._create_cursor_bitmap()

        _user32.SetTimer(self._hwnd, 1, 16, None)  # ~60fps
        win32gui.ShowWindow(self._hwnd, win32con.SW_SHOWNOACTIVATE)

        while self._running:
            while True:
                handled, msg = win32gui.PeekMessage(None, 0, 0, win32con.PM_REMOVE)
                if not handled:
                    break
                win32gui.TranslateMessage(msg)
                win32gui.DispatchMessage(msg)

        if self._hwnd:
            _user32.KillTimer(self._hwnd, 1)
            win32gui.DestroyWindow(self._hwnd)
            self._hwnd = None

    def _create_cursor_bitmap(self) -> None:
        """在内存 DC 中预先绘制光标图案。"""
        hdc_screen = win32gui.GetDC(0)
        self._hdc_mem = win32gui.CreateCompatibleDC(hdc_screen)
        self._bmp = win32gui.CreateCompatibleBitmap(hdc_screen, CURSOR_SIZE, CURSOR_SIZE)
        self._old_bmp = win32gui.SelectObject(self._hdc_mem, self._bmp)

        # 黑色背景（将被 color-key 透明化）
        brush = win32gui.CreateSolidBrush(win32api.RGB(0, 0, 0))
        win32gui.FillRect(self._hdc_mem, (0, 0, CURSOR_SIZE, CURSOR_SIZE), brush)
        win32gui.DeleteObject(brush)

        # 红色箭头
        pen = win32gui.CreatePen(win32con.PS_SOLID, 1, win32api.RGB(255, 60, 60))
        brush_r = win32gui.CreateSolidBrush(win32api.RGB(255, 60, 60))
        old_pen = win32gui.SelectObject(self._hdc_mem, pen)
        old_brush = win32gui.SelectObject(self._hdc_mem, brush_r)

        pts = [(3, 3), (18, 18), (12, 18), (18, 28), (15, 31), (9, 22), (4, 24)]
        win32gui.Polygon(self._hdc_mem, pts)

        # 白色描边
        pen_w = win32gui.CreatePen(win32con.PS_SOLID, 1, win32api.RGB(255, 255, 255))
        win32gui.SelectObject(self._hdc_mem, pen_w)
        win32gui.Polygon(self._hdc_mem, pts)
        win32gui.DeleteObject(pen_w)

        win32gui.SelectObject(self._hdc_mem, old_pen)
        win32gui.SelectObject(self._hdc_mem, old_brush)
        win32gui.DeleteObject(pen)
        win32gui.DeleteObject(brush_r)
        win32gui.ReleaseDC(0, hdc_screen)

    def _redraw(self) -> None:
        if self._hwnd is None:
            return

        with self._lock:
            x, y = self._x, self._y

        # 移动窗口到光标位置
        win32gui.SetWindowPos(
            self._hwnd, win32con.HWND_TOPMOST,
            x, y, CURSOR_SIZE, CURSOR_SIZE,
            win32con.SWP_NOACTIVATE | win32con.SWP_SHOWWINDOW | win32con.SWP_NOSIZE,
        )

        # 绘制光标
        hdc = win32gui.GetDC(self._hwnd)
        win32gui.BitBlt(
            hdc, 0, 0, CURSOR_SIZE, CURSOR_SIZE,
            self._hdc_mem, 0, 0, win32con.SRCCOPY,
        )
        win32gui.ReleaseDC(self._hwnd, hdc)
