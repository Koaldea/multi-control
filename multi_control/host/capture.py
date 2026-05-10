"""DXCam 屏幕采集 + JPEG 压缩 + 帧差计算."""

import time
from typing import Optional

import cv2
import dxcam
import numpy as np


class ScreenCapture:
    """高速屏幕采集器，支持帧差传输优化带宽."""

    def __init__(self, target_fps: int = 30, jpeg_quality: int = 75):
        self.target_fps = target_fps
        self.jpeg_quality = jpeg_quality
        self._camera: Optional[dxcam.DXCamera] = None
        self._prev_frame: Optional[np.ndarray] = None
        self._running = False
        self._frame_count = 0
        self._full_frame_interval = 60  # 每 N 帧发一次全量帧防止画面漂移

    @property
    def camera(self) -> dxcam.DXCamera:
        if self._camera is None:
            raise RuntimeError("Capture not started")
        return self._camera

    def start(self) -> None:
        self._camera = dxcam.create(output_color="BGR")
        self._camera.start(target_fps=self.target_fps, video_mode=True)
        self._running = True

    def stop(self) -> None:
        self._running = False
        if self._camera:
            self._camera.stop()
            self._camera.release()
            self._camera = None

    def get_frame(self) -> tuple[dict, bytes]:
        """获取下一帧 → (metadata, jpeg_bytes)."""
        frame = self.camera.get_latest_frame()
        while frame is None:
            time.sleep(0.001)
            frame = self.camera.get_latest_frame()

        self._frame_count += 1

        # 首帧或定期全量帧
        if self._prev_frame is None or self._frame_count % self._full_frame_interval == 0:
            result = self._encode_full(frame)
        else:
            rects = self._compute_dirty_rects(self._prev_frame, frame)
            if rects is None:
                result = self._encode_full(frame)
            else:
                result = self._encode_diff(frame, rects)

        self._prev_frame = frame
        return result

    def _encode_full(self, frame: np.ndarray) -> tuple[dict, bytes]:
        h, w = frame.shape[:2]
        ok, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality])
        if not ok:
            raise RuntimeError("JPEG encode failed")
        meta = {
            "type": "full",
            "width": w,
            "height": h,
            "format": "jpeg",
            "quality": self.jpeg_quality,
            "seq": self._frame_count,
        }
        return meta, jpeg.tobytes()

    def _encode_diff(self, frame: np.ndarray, rects: list[tuple[int, int, int, int]]) -> tuple[dict, bytes]:
        h, w = frame.shape[:2]
        meta = {
            "type": "diff",
            "width": w,
            "height": h,
            "seq": self._frame_count,
            "rects": rects,
        }
        # 拼接所有脏矩形的 JPEG
        parts = []
        for rx, ry, rw, rh in rects:
            roi = frame[ry:ry + rh, rx:rx + rw]
            ok, jpeg = cv2.imencode(".jpg", roi, [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality])
            if not ok:
                continue
            data = jpeg.tobytes()
            parts.append(len(data).to_bytes(4, "little") + data)

        return meta, b"".join(parts)

    def _compute_dirty_rects(
        self, prev: np.ndarray, curr: np.ndarray
    ) -> Optional[list[tuple[int, int, int, int]]]:
        """计算脏矩形列表；变化过大时返回 None 表示应发全量帧."""
        prev_gray = cv2.cvtColor(prev, cv2.COLOR_BGR2GRAY)
        curr_gray = cv2.cvtColor(curr, cv2.COLOR_BGR2GRAY)
        diff = cv2.absdiff(prev_gray, curr_gray)
        _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (20, 20))
        dilated = cv2.dilate(thresh, kernel)
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        rects = []
        for cnt in contours:
            rx, ry, rw, rh = cv2.boundingRect(cnt)
            rects.append((rx, ry, rw, rh))

        rects = _merge_rects(rects)

        if not rects:
            return None

        total_area = sum(rw * rh for _, _, rw, rh in rects)
        frame_area = curr.shape[1] * curr.shape[0]
        if total_area > frame_area * 0.6:
            return None

        return rects


def _merge_rects(rects: list[tuple[int, int, int, int]], gap: int = 16) -> list[tuple[int, int, int, int]]:
    """合并间距小于 gap 的重叠/相邻矩形，减少小碎片."""
    if len(rects) <= 1:
        return rects

    rects = list(rects)
    merged = True
    while merged:
        merged = False
        new_rects = []
        used = [False] * len(rects)
        for i in range(len(rects)):
            if used[i]:
                continue
            ax, ay, aw, ah = rects[i]
            for j in range(i + 1, len(rects)):
                if used[j]:
                    continue
                bx, by, bw, bh = rects[j]
                # 扩展后是否相交
                ax1, ay1 = ax - gap, ay - gap
                ax2, ay2 = ax + aw + gap, ay + ah + gap
                bx1, by1 = bx - gap, by - gap
                bx2, by2 = bx + bw + gap, by + bh + gap
                if ax1 < bx2 and ax2 > bx1 and ay1 < by2 and ay2 > by1:
                    nx = min(ax, bx)
                    ny = min(ay, by)
                    nw = max(ax + aw, bx + bw) - nx
                    nh = max(ay + ah, by + bh) - ny
                    rects[i] = (nx, ny, nw, nh)
                    used[j] = True
                    merged = True
            new_rects.append(rects[i])
        rects = new_rects
    return rects
