"""消息协议定义 — 帧传输、输入指令、LAN 发现."""

import json
import struct
from typing import Any

# 端口约定
PORT_DISCOVERY = 5554
PORT_STREAM = 5555
PORT_COMMAND = 5556
BROADCAST_ADDR = "255.255.255.255"

# ZMQ topic 前缀
TOPIC_SCREEN = b"screen"
TOPIC_CURSOR = b"cursor"


def pack_frame(metadata: dict, jpeg_data: bytes) -> list[bytes]:
    """打包帧消息为 ZMQ multipart: [topic, json_meta, jpeg_bytes]."""
    return [TOPIC_SCREEN, json.dumps(metadata).encode(), jpeg_data]


def unpack_frame(parts: list[bytes]) -> tuple[dict, bytes]:
    """解包帧消息 → (metadata, jpeg_data)."""
    return json.loads(parts[1].decode()), bytes(parts[2])


def pack_input(seq: int, events: list[dict]) -> bytes:
    """打包输入指令 → JSON bytes."""
    return json.dumps({"seq": seq, "events": events}).encode()


def unpack_input(data: bytes) -> dict:
    """解包输入指令 → dict."""
    return json.loads(data)


def pack_input_ack(seq: int, status: str = "ok") -> bytes:
    """打包输入确认."""
    return json.dumps({"seq": seq, "status": status}).encode()


def pack_discovery(msg_type: str, **kwargs: Any) -> bytes:
    """打包 LAN 发现消息."""
    msg = {"type": msg_type, "version": 1, **kwargs}
    return json.dumps(msg).encode()


def unpack_discovery(data: bytes) -> dict:
    """解包 LAN 发现消息."""
    return json.loads(data)


def encode_dirty_rects(rects: list[tuple[int, int, int, int]]) -> bytes:
    """编码脏矩形列表为二进制: count + 每个 (x,y,w,h) 用 4*uint16."""
    buf = struct.pack("<H", len(rects))
    for x, y, w, h in rects:
        buf += struct.pack("<HHHH", x, y, w, h)
    return buf


def decode_dirty_rects(data: bytes) -> list[tuple[int, int, int, int]]:
    """解码脏矩形列表."""
    count = struct.unpack("<H", data[:2])[0]
    rects = []
    off = 2
    for _ in range(count):
        x, y, w, h = struct.unpack("<HHHH", data[off:off + 8])
        rects.append((x, y, w, h))
        off += 8
    return rects
