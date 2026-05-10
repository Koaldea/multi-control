"""屏幕流传输 — ZMQ PUB/SUB."""

import json
import threading
from typing import Optional

import zmq

from ..protocol import PORT_STREAM, TOPIC_SCREEN, pack_frame, unpack_frame


class ScreenPublisher:
    """被控端：将采集的屏幕帧通过 PUB socket 广播."""

    def __init__(self, port: int = PORT_STREAM):
        self.port = port
        self._ctx: Optional[zmq.Context] = None
        self._socket: Optional[zmq.Socket] = None

    def bind(self) -> str:
        """绑定并返回 bind 地址."""
        self._ctx = zmq.Context()
        self._socket = self._ctx.socket(zmq.PUB)
        self._socket.setsockopt(zmq.SNDHWM, 4)
        addr = f"tcp://*:{self.port}"
        self._socket.bind(addr)
        return addr

    def send_frame(self, metadata: dict, jpeg_data: bytes) -> None:
        """发送一帧."""
        parts = pack_frame(metadata, jpeg_data)
        self._socket.send_multipart(parts)

    def close(self) -> None:
        if self._socket:
            self._socket.close()
        if self._ctx:
            self._ctx.term()


class ScreenSubscriber:
    """控制端：通过 SUB socket 接收屏幕帧."""

    def __init__(self, host_ip: str, port: int = PORT_STREAM):
        self.host_ip = host_ip
        self.port = port
        self._ctx: Optional[zmq.Context] = None
        self._socket: Optional[zmq.Socket] = None

    def connect(self) -> None:
        self._ctx = zmq.Context()
        self._socket = self._ctx.socket(zmq.SUB)
        self._socket.setsockopt(zmq.SUBSCRIBE, TOPIC_SCREEN)
        self._socket.setsockopt(zmq.RCVHWM, 4)
        addr = f"tcp://{self.host_ip}:{self.port}"
        self._socket.connect(addr)

    def recv_frame(self, timeout_ms: int = 10) -> Optional[tuple[dict, bytes]]:
        """非阻塞接收一帧，超时返回 None."""
        if self._socket.poll(timeout_ms, zmq.POLLIN):
            parts = self._socket.recv_multipart()
            return unpack_frame(parts)
        return None

    def close(self) -> None:
        if self._socket:
            self._socket.close()
        if self._ctx:
            self._ctx.term()
