"""被控端入口 — 启动屏幕共享，等待控制端连接."""

import socket
import sys
import threading

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import QApplication, QLabel, QMainWindow, QPushButton, QVBoxLayout, QWidget

from .capture import ScreenCapture
from .cursor_overlay import CursorOverlay
from .input_inject import (
    inject_key,
    inject_mouse_button,
    inject_mouse_wheel,
)
from ..network.command import CommandReceiver
from ..network.discovery import DiscoveryHost
from ..network.stream import ScreenPublisher


class HostPanel(QMainWindow):
    """被控端控制面板."""

    def __init__(self, capture: ScreenCapture, publisher: ScreenPublisher):
        super().__init__()
        self._capture = capture
        self._publisher = publisher
        self._running = True
        self._frame_seq = 0

        self.setWindowTitle("Multi-Control — Host")
        self.setFixedSize(320, 200)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowMaximizeButtonHint)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(12)

        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)

        self._status_lbl = QLabel("🟢 正在共享桌面")
        self._status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._status_lbl)

        info = QLabel(f"主机: {hostname}\nIP: {ip}\n端口: 5555 (画面) / 5556 (输入)")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info)

        self._conn_lbl = QLabel("等待连接...")
        self._conn_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._conn_lbl)

        stop_btn = QPushButton("停止共享")
        stop_btn.clicked.connect(self._stop)
        layout.addWidget(stop_btn)

        # 定时器：检查连接状态
        self._timer = QTimer()
        self._timer.timeout.connect(self._check_status)
        self._timer.start(1000)

    def _check_status(self) -> None:
        if hasattr(self._publisher, "_socket") and self._publisher._socket:
            self._conn_lbl.setText("已连接: 1 个控制端")
        else:
            self._conn_lbl.setText("等待连接...")

    def _stop(self) -> None:
        self._running = False
        self._status_lbl.setText("🔴 已停止")
        self.close()


def run_host() -> None:
    """启动被控端."""
    hostname = socket.gethostname()

    # ── 初始化各模块 ─────────────────────────
    capture = ScreenCapture(target_fps=30, jpeg_quality=75)
    publisher = ScreenPublisher()
    cmd_receiver = CommandReceiver()
    overlay = CursorOverlay()
    discovery = DiscoveryHost(hostname)

    # ── 绑定网络端口 ─────────────────────────
    try:
        capture.start()
    except Exception as e:
        print(f"屏幕采集初始化失败: {e}")
        print("尝试用管理员权限运行...")
        sys.exit(1)

    stream_addr = publisher.bind()
    cmd_addr = cmd_receiver.bind()
    discovery.start()
    overlay.start()

    print(f"被控端已启动 — {hostname}")
    print(f"  画面: {stream_addr}")
    print(f"  输入: {cmd_addr}")

    # ── 输入接收线程 ─────────────────────────
    remote_x = 0
    remote_y = 0

    def input_loop() -> None:
        nonlocal remote_x, remote_y
        while app_running[0]:
            msg = cmd_receiver.recv_input(timeout_ms=10)
            if msg is None:
                continue
            for evt in msg.get("events", []):
                etype = evt.get("type")
                try:
                    if etype == "mouse_move":
                        x, y = evt["x"], evt["y"]
                        remote_x, remote_y = x, y
                        overlay.update(x, y)
                    elif etype == "mouse_button":
                        inject_mouse_button(evt["button"], evt["pressed"], remote_x, remote_y)
                    elif etype == "mouse_wheel":
                        inject_mouse_wheel(evt["delta"], remote_x, remote_y)
                    elif etype == "key":
                        vk = evt.get("vk")
                        if vk is not None:
                            inject_key(vk, evt["pressed"])
                    elif etype == "quit":
                        app_running[0] = False
                        return
                except Exception as exc:
                    print(f"输入注入失败: {etype}: {exc}")

    app_running = [True]
    input_thread = threading.Thread(target=input_loop, daemon=True)
    input_thread.start()

    # ── 屏幕采集 + 发布循环（独立线程） ──────
    def capture_loop() -> None:
        while app_running[0]:
            try:
                meta, jpeg_data = capture.get_frame()
                publisher.send_frame(meta, jpeg_data)
            except Exception as e:
                print(f"采集/发送错误: {e}")
                break

    capture_thread = threading.Thread(target=capture_loop, daemon=True)
    capture_thread.start()

    # ── PyQt6 控制面板 ──────────────────────
    app = QApplication(sys.argv)
    panel = HostPanel(capture, publisher)

    def on_quit() -> None:
        app_running[0] = False

    app.aboutToQuit.connect(on_quit)
    panel.show()
    app.exec()

    # ── 清理 ────────────────────────────────
    app_running[0] = False
    capture.stop()
    publisher.close()
    cmd_receiver.close()
    overlay.stop()
    discovery.stop()
    print("被控端已关闭")
