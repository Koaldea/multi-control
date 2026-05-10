"""LAN 发现 — UDP 广播自动发现被控端."""

import json
import socket
import threading
from typing import Optional

from ..protocol import PORT_DISCOVERY, BROADCAST_ADDR, pack_discovery, unpack_discovery


class DiscoveryHost:
    """被控端：监听 UDP 发现请求并回复."""

    def __init__(self, hostname: str, stream_port: int = 5555, command_port: int = 5556):
        self._hostname = hostname
        self._stream_port = stream_port
        self._command_port = command_port
        self._sock: Optional[socket.socket] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self._sock.bind(("0.0.0.0", PORT_DISCOVERY))
        self._sock.settimeout(0.5)

        self._running = True
        self._thread = threading.Thread(target=self._listen, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass

    def _listen(self) -> None:
        while self._running:
            try:
                data, addr = self._sock.recvfrom(1024)
                msg = unpack_discovery(data)
                if msg.get("type") == "discover":
                    reply = pack_discovery(
                        "announce",
                        hostname=self._hostname,
                        stream_port=self._stream_port,
                        command_port=self._command_port,
                    )
                    self._sock.sendto(reply, addr)
            except socket.timeout:
                continue
            except OSError:
                break


class DiscoveryViewer:
    """控制端：发送 UDP 广播发现被控端."""

    def __init__(self, timeout: float = 2.0):
        self._timeout = timeout

    def discover(self) -> list[dict]:
        """广播发现，返回可用的被控端列表."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(self._timeout)

        try:
            # 发送广播
            msg = pack_discovery("discover")
            sock.sendto(msg, (BROADCAST_ADDR, PORT_DISCOVERY))

            # 收集回复
            hosts = []
            while True:
                try:
                    data, addr = sock.recvfrom(1024)
                    info = unpack_discovery(data)
                    if info.get("type") == "announce":
                        info["ip"] = addr[0]
                        hosts.append(info)
                except socket.timeout:
                    break
            return hosts
        finally:
            sock.close()
