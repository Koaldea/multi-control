"""控制端入口 — 连接被控端，显示远程桌面，发送本地输入."""

import sys

import pygame

from .display import RemoteDisplay
from .input_send import InputCapture
from ..network.command import CommandSender
from ..network.discovery import DiscoveryViewer
from ..network.stream import ScreenSubscriber


def run_viewer(host_ip: str | None = None) -> None:
    """启动控制端."""
    # ── 发现或直连 ───────────────────────────
    if host_ip is None:
        print("正在扫描局域网内的被控端...")
        discovery = DiscoveryViewer(timeout=2.0)
        hosts = discovery.discover()
        if not hosts:
            print("未发现任何被控端。")
            print("用法: python main.py viewer <host_ip>")
            sys.exit(1)
        print(f"发现 {len(hosts)} 个被控端:")
        for i, h in enumerate(hosts):
            print(f"  [{i}] {h['hostname']} ({h['ip']})")
        choice = input("选择 (输入序号): ").strip()
        try:
            selected = hosts[int(choice)]
        except (ValueError, IndexError):
            print("无效选择")
            sys.exit(1)
        host_ip = selected["ip"]
        stream_port = selected.get("stream_port", 5555)
        cmd_port = selected.get("command_port", 5556)
    else:
        stream_port = 5555
        cmd_port = 5556

    print(f"连接到 {host_ip}...")

    # ── 初始化网络 ───────────────────────────
    sub = ScreenSubscriber(host_ip, stream_port)
    sender = CommandSender(host_ip, cmd_port)

    try:
        sub.connect()
        sender.connect()
    except Exception as e:
        print(f"连接失败: {e}")
        sys.exit(1)

    # ── 等待首帧以确定窗口尺寸 ───────────────
    print("等待画面...")
    display = RemoteDisplay(host_ip, stream_port)
    while True:
        result = sub.recv_frame(timeout_ms=500)
        if result is not None:
            meta, data = result
            display.init_display(meta["width"], meta["height"])
            display.process_frame(meta, data)
            break

    # ── 输入捕获 ────────────────────────────
    input_cap = InputCapture(display, sender)

    # ── 主循环 ──────────────────────────────
    print("已连接。按 Esc 退出。")
    fps_target = 60

    while display.running:
        # 接收画面
        result = sub.recv_frame(timeout_ms=2)
        if result is not None:
            meta, data = result
            display.process_frame(meta, data)

        # 渲染
        display.render()

        # 捕获并发送输入
        input_cap.collect_events()
        input_cap.flush()

        # 检查是否退出
        if not display.running:
            break

        display.tick(fps_target)

    # ── 清理 ────────────────────────────────
    sub.close()
    sender.close()
    display.close()
    print("控制端已关闭")
