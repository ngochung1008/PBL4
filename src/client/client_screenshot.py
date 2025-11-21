# client/client_screenshot.py

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
    def __init__(self, fps=15, quality=60, max_dimension=1280, detect_delta=True):
        self.fps = fps
        self.quality = quality
        self.max_dimension = max_dimension
        self.detect_delta = False

        self._first_frame = True
        self._prev_image = None
        self._force_full = False
        self.stop = False
        self.frame_seq = 0
        self._lock = threading.Lock()
        self.FULL_FRAME_INTERVAL = 60.0 # <--- [SỬA ĐỔI] 30 giây
        self.last_full_frame_ts = 0.0 # <--- [SỬA ĐỔI] Thêm biến thời gian

    def _resize_if_needed(self, img):
        w, h = img.size
        long_edge = max(w, h)
        if self.max_dimension and long_edge > self.max_dimension:
            scale = float(self.max_dimension) / long_edge
            img = img.resize((int(w*scale), int(h*scale)), RESAMPLE_MODE)
        return img

    def _encode_jpeg(self, img):
        bio = io.BytesIO()
        if img.mode != "RGB":
            img = img.convert("RGB")
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
            # [SỬA] Đảm bảo prev_image được khởi tạo là ảnh thang xám
            self._prev_image = img.convert("L")
            return None
            
        # 1. Tính toán sự khác biệt (trên ảnh thang xám)
        diff = ImageChops.difference(img.convert("L"), self._prev_image)
        
        # 2. Áp dụng Threshold
        threshold_value = 30
        mask = diff.point(lambda p: 255 if p > threshold_value else 0) 
        
        # 3. Tính toán bounding box từ mask
        bbox = mask.getbbox()
        
        if bbox is not None:
            # [SỬA] Cập nhật ảnh cũ sang ảnh mới (nếu có thay đổi)
            self._prev_image = img.convert("L") 
            
        return bbox

    def force_full_frame(self):
        with self._lock:
            self._force_full = True

    def capture_loop(self, callback):
        interval = 1.0 / self.fps
        print(f"[ClientScreenshot] Bắt đầu capture loop (Luôn gửi FULL frame)...")

        while not self.stop:
            start_time = time.perf_counter()
            
            try:
                # 1. Chụp ảnh
                img = self.capture_once()

                # 2. Mặc định luôn là FULL FRAME (bbox = None)
                bbox = None 
                
                # 3. Encode JPEG
                jpg_bytes = self._encode_jpeg(img)
                width, height = img.size
                
                ts_ms = int(time.time() * 1000)
                seq = self.frame_seq
                self.frame_seq += 1

                # 4. Gửi callback
                # print(f"[ClientScreenshot] Gửi frame {seq}, size={len(jpg_bytes)} bytes")
                callback(width, height, jpg_bytes, bbox, img, seq, ts_ms)

            except Exception as e:
                print(f"[ClientScreenshot] Lỗi: {e}")

            # Điều chỉnh FPS
            elapsed = time.perf_counter() - start_time
            time.sleep(max(0, interval - elapsed))