# client/client_screenshot.py

# from mss import mss
import pyautogui
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
        # with mss() as sct:
        #     monitor = sct.monitors[0]
        #     sct_img = sct.grab(monitor)
        #     img = Image.frombytes("RGB", sct_img.size, sct_img.rgb)
        #     return self._resize_if_needed(img)

        img = pyautogui.screenshot()
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
        print(f"[ClientScreenshot] Bắt đầu capture loop (Hybrid Mode: Full + Rect)...")

        while not self.stop:
            start_time = time.perf_counter()
            
            try:
                # 1. Chụp ảnh màn hình hiện tại
                img = self.capture_once()
                full_width, full_height = img.size
                
                # 2. Kiểm tra xem có CẦN gửi Full Frame không?
                # - Là frame đầu tiên?
                # - Bị ép buộc (force_full)?
                # - Đã quá lâu chưa gửi Full Frame (30s)?
                now = time.time()
                is_time_for_full = (now - self.last_full_frame_ts) >= self.FULL_FRAME_INTERVAL
                should_send_full = self._first_frame or self._force_full or is_time_for_full

                bbox = None # Mặc định là None (nghĩa là Full Frame)

                if should_send_full:
                    # --- GỬI FULL FRAME ---
                    self._first_frame = False
                    self._force_full = False
                    self.last_full_frame_ts = now
                    
                    # Cập nhật ảnh tham chiếu (để so sánh cho lần sau)
                    self._prev_image = img.convert("L") 
                    
                    # bbox vẫn là None -> Code phía dưới sẽ hiểu là Full Frame
                    
                else:
                    # --- GỬI RECT FRAME (Đây là đoạn bạn cần bật lại) ---
                    # Tính toán vùng thay đổi so với ảnh trước
                    bbox = self.compute_delta_bbox(img)

                # 3. Xử lý gửi
                # Nếu là chế độ Rect (không phải Full) mà bbox là None (nghĩa là màn hình đứng im, không thay đổi)
                # -> Thì KHÔNG gửi gì cả để tiết kiệm băng thông.
                if not should_send_full and bbox is None:
                    # Ngủ bù thời gian rồi tiếp tục vòng lặp
                    elapsed = time.perf_counter() - start_time
                    time.sleep(max(0, interval - elapsed))
                    continue

                # 4. Cắt ảnh và Encode
                if bbox:
                    # [RECT] Cắt vùng thay đổi
                    crop_img = img.crop(bbox)
                    jpg_bytes = self._encode_jpeg(crop_img)
                    pass 
                else:
                    # [FULL] Lấy toàn bộ ảnh
                    jpg_bytes = self._encode_jpeg(img)

                ts_ms = int(time.time() * 1000)
                seq = self.frame_seq
                self.frame_seq += 1

                # 5. Gửi qua callback (vào Sender)
                sent_ok = callback(full_width, full_height, jpg_bytes, bbox, img, seq, ts_ms)
                if sent_ok is False:
                    time.sleep(0.05)

            except Exception as e:
                print(f"[ClientScreenshot] Lỗi: {e}")
                # import traceback
                # traceback.print_exc()

            # Điều chỉnh FPS
            elapsed = time.perf_counter() - start_time
            time.sleep(max(0, interval - elapsed))