# client_screenshot.py

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
        self.detect_delta = detect_delta
        self._first_frame = True
        self._prev_image = None
        self.stop = False

    # Hàm resize nếu màn hình lớn
    def _resize_if_needed(self, img):
        w, h = img.size
        long_edge = max(w, h)
        if self.max_dimension and long_edge > self.max_dimension:
            scale = float(self.max_dimension) / long_edge
            new_w = int(w * scale)
            new_h = int(h * scale)
            img = img.resize((new_w, new_h), RESAMPLE_MODE)
        return img

    # Hàm mã hóa JPEG 
    def _encode_jpeg(self, img):
        bio = io.BytesIO()
        img.save(bio, format="JPEG", quality=self.quality)
        return bio.getvalue()

    # Hàm chụp ảnh 1 lần 
    def capture_once(self):
        with mss() as sct:
            monitor = sct.monitors[0]
            sct_img = sct.grab(monitor) # lấy raw pixel data
            img = Image.frombytes("RGB", sct_img.size, sct_img.rgb)
            img = self._resize_if_needed(img) # nén ảnh 
            return img

    # phát hiện vùng thay đổi giữa 2 frame 
    def compute_delta_bbox(self, img):
        """ Trả về bbox (left, upper, right, lower) nếu có sự khác biệt so với frame trước,
        hoặc None nếu không khác biệt (hoặc detect_delta=False). """
        if not self.detect_delta:
            return None
        if self._prev_image is None:
            self._prev_image = img.convert("L")
            return None
        # diff = ImageChops.difference(img, self._prev_image) # so sánh với ảnh trước
        diff = ImageChops.difference(img.convert("L"), self._prev_image)
        bbox = diff.getbbox()  # nếu bbox is None => không khác biệt
        return bbox

    # vòng lặp liên tục 
    def capture_loop(self, callback):
        """
        callback(width, height, jpg_bytes, bbox, pil_image)
        - Gửi full frame đầu tiên
        - Các frame sau chỉ gửi delta (nếu có khác biệt)
        - Tự điều chỉnh FPS
        """
        interval = 1.0 / self.fps
        self._first_frame = True
        self._prev_image = None

        while not self.stop:
            start_time = time.perf_counter()

            img = self.capture_once()

            # Frame đầu tiên luôn gửi full
            bbox = None
            if not self._first_frame and self.detect_delta:
                bbox = self.compute_delta_bbox(img)
            else:
                self._first_frame = False

            # Nếu không có thay đổi thì bỏ qua
            if bbox is None and not self._first_frame:
                elapsed = time.perf_counter() - start_time
                sleep_time = max(0, interval - elapsed)
                time.sleep(sleep_time)
                continue

            # Encode ảnh (full hoặc delta)
            if bbox:
                region = img.crop(bbox)
                jpg_bytes = self._encode_jpeg(region)
            else:
                jpg_bytes = self._encode_jpeg(img)

            width, height = img.size
            # Cập nhật ảnh trước (dạng grayscale)
            self._prev_image = img.convert("L")

            # Gọi callback để enqueue
            try:
                callback(width, height, jpg_bytes, bbox, img)
            except Exception as e:
                print("[CLIENT SCREENSHOT] Callback error:", e)

            # Duy trì FPS
            elapsed = time.perf_counter() - start_time
            sleep_time = max(0, interval - elapsed)
            time.sleep(sleep_time)