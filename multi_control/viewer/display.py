"""Pygame 窗口 — 显示远程桌面画面."""

from typing import Optional

import cv2
import numpy as np
import pygame


class RemoteDisplay:
    """渲染远程桌面画面的 Pygame 窗口."""

    def __init__(self, host_ip: str, stream_port: int = 5555):
        self._host_ip = host_ip
        self._stream_port = stream_port
        self._screen: Optional[pygame.Surface] = None
        self._frame: Optional[np.ndarray] = None  # 当前完整帧缓存 (BGR)
        self.window_size: tuple[int, int] = (0, 0)
        self._clock = pygame.time.Clock()
        self._running = False
        self._fps = 0.0
        self.event_count = 0

    @property
    def running(self) -> bool:
        return self._running

    def init_display(self, width: int, height: int) -> None:
        """首帧到达后初始化窗口."""
        pygame.init()
        pygame.display.set_caption("Multi-Control — Viewer")
        self._screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
        self.window_size = (width, height)
        self._frame = np.zeros((height, width, 3), dtype=np.uint8)
        self._running = True

    def process_frame(self, metadata: dict, data: bytes) -> None:
        """解码并更新画面."""
        if self._frame is None:
            return

        if metadata["type"] == "full":
            arr = np.frombuffer(data, dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is not None:
                h, w = img.shape[:2]
                self._frame = img
                self.window_size = (w, h)
        elif metadata["type"] == "diff":
            rects = metadata.get("rects", [])
            off = 0
            for rx, ry, rw, rh in rects:
                size = int.from_bytes(data[off:off + 4], "little")
                off += 4
                arr = np.frombuffer(data[off:off + size], dtype=np.uint8)
                off += size
                roi = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                if roi is not None:
                    self._frame[ry:ry + rh, rx:rx + rw] = roi

    def render(self) -> None:
        """绘制当前帧到 Pygame 窗口."""
        if self._frame is None or self._screen is None:
            return

        # BGR → RGB for Pygame
        rgb = cv2.cvtColor(self._frame, cv2.COLOR_BGR2RGB)
        # pygame.surfarray.make_surface 要求 shape=(W, H, 3)
        # OpenCV 输出是 (H, W, 3) → 需要转置
        rgb = np.transpose(rgb, (1, 0, 2))
        surf = pygame.surfarray.make_surface(np.ascontiguousarray(rgb))

        # 缩放到当前窗口大小
        win_w, win_h = self._screen.get_size()
        if (win_w, win_h) != self.window_size:
            surf = pygame.transform.scale(surf, (win_w, win_h))

        self._screen.blit(surf, (0, 0))
        self._update_fps_caption()
        pygame.display.flip()

    def tick(self, fps: int = 60) -> float:
        """限制帧率，返回 delta_time 秒."""
        return self._clock.tick(fps) / 1000.0

    def _update_fps_caption(self) -> None:
        self._fps = self._clock.get_fps()
        pygame.display.set_caption(
            f"Multi-Control | FPS:{self._fps:.0f} evt:{self.event_count}"
        )

    def close(self) -> None:
        self._running = False
        pygame.quit()
