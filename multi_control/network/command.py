"""输入指令通道 — ZMQ DEALER/ROUTER（无状态，不支持 ack，适合实时输入）."""

from typing import Optional

import zmq

from ..protocol import PORT_COMMAND, pack_input, unpack_input


class CommandReceiver:
    """被控端：ROUTER socket 接收输入指令."""

    def __init__(self, port: int = PORT_COMMAND):
        self.port = port
        self._ctx: Optional[zmq.Context] = None
        self._socket: Optional[zmq.Socket] = None

    def bind(self) -> str:
        self._ctx = zmq.Context()
        self._socket = self._ctx.socket(zmq.ROUTER)
        self._socket.setsockopt(zmq.RCVHWM, 20)
        addr = f"tcp://*:{self.port}"
        self._socket.bind(addr)
        return addr

    def recv_input(self, timeout_ms: int = 10) -> Optional[dict]:
        """非阻塞接收输入指令，超时返回 None.
        返回的 dict 中 .sender_id 保存对端标识（可忽略）。
        """
        if self._socket.poll(timeout_ms, zmq.POLLIN):
            parts = self._socket.recv_multipart()
            # ROUTER: [identity, ...data]
            msg = unpack_input(parts[-1])
            if len(parts) > 1:
                msg["_sender_id"] = parts[0]
            return msg
        return None

    def close(self) -> None:
        if self._socket:
            self._socket.close()
        if self._ctx:
            self._ctx.term()


class CommandSender:
    """控制端：DEALER socket 发送输入指令（fire-and-forget）."""

    def __init__(self, host_ip: str, port: int = PORT_COMMAND):
        self.host_ip = host_ip
        self.port = port
        self._ctx: Optional[zmq.Context] = None
        self._socket: Optional[zmq.Socket] = None
        self._seq = 0

    def connect(self) -> None:
        self._ctx = zmq.Context()
        self._socket = self._ctx.socket(zmq.DEALER)
        self._socket.setsockopt(zmq.SNDHWM, 20)
        self._socket.setsockopt(zmq.LINGER, 0)
        self._socket.connect(f"tcp://{self.host_ip}:{self.port}")

    def send_input(self, events: list[dict]) -> bool:
        """发送输入事件（fire-and-forget，不等待确认）."""
        if not events:
            return True
        self._seq += 1
        try:
            self._socket.send(pack_input(self._seq, events), flags=zmq.NOBLOCK)
            return True
        except zmq.Again:
            return False

    def close(self) -> None:
        if self._socket:
            self._socket.close()
        if self._ctx:
            self._ctx.term()
