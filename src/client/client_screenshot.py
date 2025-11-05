# client_screenshot.py
# -*- coding: utf-8 -*-
"""
ClientScreenshot
- Chụp màn hình (mss)
- Resize (max_dimension)
- Encode JPEG
- Giữ frame hiện tại và so sánh với frame trước để lấy bounding box vùng khác biệt (delta).
- API:
    capturer = ClientScreenshot(fps=2, quality=75, max_dimension=1280)
    capturer.capture_loop(callback)  # callback(width, height, jpg_bytes, bbox_or_None, pil_image)
    capturer.stop = True  # để dừng loop
"""

from mss import mss
from PIL import Image, ImageChops
import io
import time

try:
    RESAMPLE_MODE = Image.Resampling.LANCZOS
except AttributeError:
    RESAMPLE_MODE = Image.ANTIALIAS


class ClientScreenshot:
    def __init__(self, fps=2, quality=75, max_dimension=1280, detect_delta=True):
        self.fps = fps
        self.quality = quality
        self.max_dimension = max_dimension
        self.stop = False
        self.detect_delta = detect_delta
        self._prev_image = None

    def _resize_if_needed(self, img):
        w, h = img.size
        long_edge = max(w, h)
        if self.max_dimension and long_edge > self.max_dimension:
            scale = float(self.max_dimension) / long_edge
            new_w = int(w * scale)
            new_h = int(h * scale)
            img = img.resize((new_w, new_h), RESAMPLE_MODE)
        return img

    def _encode_jpeg(self, img):
        bio = io.BytesIO()
        img.save(bio, format="JPEG", quality=self.quality)
        return bio.getvalue()

    def capture_once(self):
        with mss() as sct:
            monitor = sct.monitors[0]
            sct_img = sct.grab(monitor)
            img = Image.frombytes("RGB", sct_img.size, sct_img.rgb)
            img = self._resize_if_needed(img)
            return img

    def compute_delta_bbox(self, img):
        """
        Trả về bbox (left, upper, right, lower) nếu có sự khác biệt so với frame trước,
        hoặc None nếu không khác biệt (hoặc detect_delta=False).
        """
        if not self.detect_delta:
            return None
        if self._prev_image is None:
            return None
        diff = ImageChops.difference(img, self._prev_image)
        bbox = diff.getbbox()  # nếu bbox is None => không khác biệt
        return bbox

    def capture_loop(self, callback):
        """
        callback(width, height, jpg_bytes, bbox, pil_image)
        Nếu bbox != None => vùng khác biệt (left, upper, right, lower)
        """
        interval = 1.0 / self.fps
        while not self.stop:
            start = time.time()
            img = self.capture_once()
            bbox = self.compute_delta_bbox(img)
            jpg_bytes = self._encode_jpeg(img)
            width, height = img.size

            # cập nhật prev image (keep a copy in RGB mode)
            self._prev_image = img.copy()

            # gọi callback để gửi
            try:
                callback(width, height, jpg_bytes, bbox, img)
            except Exception as e:
                # không muốn dừng capture do lỗi ở phía sender
                print("[CAPTURER] Callback error:", e)

            elapsed = time.time() - start
            to_sleep = max(0, interval - elapsed)
            time.sleep(to_sleep)
