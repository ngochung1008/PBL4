# src/client/client_screenshot.py

from mss import mss
from PIL import Image, ImageChops
import io
import time
import threading

try:
    RESAMPLE_MODE = Image.Resampling.LANCZOS
except AttributeError:
    RESAMPLE_MODE = Image.ANTIALIAS


class ClientScreenshot:
    def __init__(self, fps=2, quality=75, max_dimension=1280, detect_delta=True):
        self.fps = fps
        self.quality = quality
        self.max_dimension = max_dimension
        self.detect_delta = detect_delta

        self._first_frame = True
        self._prev_image = None
        self._force_full = False
        self.stop = False
        self.frame_seq = 0
        self._lock = threading.Lock()

    def _resize_if_needed(self, img):
        w, h = img.size
        long_edge = max(w, h)
        if self.max_dimension and long_edge > self.max_dimension:
            scale = float(self.max_dimension) / long_edge
            img = img.resize((int(w*scale), int(h*scale)), RESAMPLE_MODE)
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
            return self._resize_if_needed(img)

    def compute_delta_bbox(self, img):
        if not self.detect_delta or self._prev_image is None:
            self._prev_image = img.convert("L")
            return None
        diff = ImageChops.difference(img.convert("L"), self._prev_image)
        bbox = diff.getbbox()
        return bbox

    def force_full_frame(self):
        with self._lock:
            self._force_full = True

    def capture_loop(self, callback):
        interval = 1.0 / self.fps
        self._first_frame = True
        self._prev_image = None

        while not self.stop:
            start_time = time.perf_counter()
            img = self.capture_once()

            bbox = None
            with self._lock:
                if self._force_full:
                    bbox = None
                    self._force_full = False

            if not self._first_frame and self.detect_delta:
                bbox = self.compute_delta_bbox(img)
            else:
                self._first_frame = False

            if bbox is None and not self._first_frame:
                elapsed = time.perf_counter() - start_time
                time.sleep(max(0, interval - elapsed))
                continue

            jpg_bytes = self._encode_jpeg(img.crop(bbox) if bbox else img)
            width, height = img.size
            ts_ms = int(time.time() * 1000)
            seq = self.frame_seq
            self.frame_seq += 1
            self._prev_image = img.convert("L")

            try:
                callback(width, height, jpg_bytes, bbox, img, seq, ts_ms)
            except Exception as e:
                print("[ClientScreenshot] Callback error:", e)

            elapsed = time.perf_counter() - start_time
            time.sleep(max(0, interval - elapsed))
