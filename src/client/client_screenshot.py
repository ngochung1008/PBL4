# client/client_screenshot.py

from mss import mss
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
    # Capture modes
    MODE_VIEW = "view"      # View-only mode: 3 giây/frame (tiết kiệm băng thông)
    MODE_CONTROL = "control"  # Control mode: Continuous (30 FPS cho smooth)
    MODE_IDLE = "idle"       # Idle mode: Không gửi (chưa có session)
    
    def __init__(self, fps=0.2, quality=85, max_dimension=1920, detect_delta=False):
        """
        fps: Frame per second (0.2 = 1 frame mỗi 5 giây, 0.33 = 1 frame mỗi 3 giây)
        quality: Chất lượng JPEG (85 = chất lượng cao)
        max_dimension: Độ phân giải tối đa (1920 = Full HD)
        detect_delta: Tắt delta detection để ưu tiên chất lượng
        """
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
        self.FULL_FRAME_INTERVAL = 60.0 # Gửi full frame mỗi 60 giây
        self.last_full_frame_ts = 0.0
        
        # Mode control: VIEW (3s/frame) vs CONTROL (continuous)
        self.mode = self.MODE_IDLE
        self.fps_view = 0.33  # ~3 giây/frame cho VIEW mode
        self.fps_control = 30  # 30 FPS cho CONTROL mode (smooth)

    def _resize_if_needed(self, img):
        w, h = img.size
        long_edge = max(w, h)
        if self.max_dimension and long_edge > self.max_dimension:
            scale = float(self.max_dimension) / long_edge
            img = img.resize((int(w*scale), int(h*scale)), RESAMPLE_MODE)
        return img

    def _encode_jpeg(self, img, adaptive=True):
        bio = io.BytesIO()
        if img.mode != "RGB":
            img = img.convert("RGB")
        
        # Adaptive quality: tăng giới hạn size lên để giữ chất lượng cao
        current_quality = self.quality
        if adaptive:
            img.save(bio, format="JPEG", quality=current_quality, optimize=True)
            size_kb = len(bio.getvalue()) / 1024
            
            # Nếu frame > 300KB, giảm quality xuống (tăng từ 80KB lên 300KB)
            if size_kb > 300:
                bio = io.BytesIO()
                current_quality = max(70, current_quality - 10)  # Giảm 10 điểm nhưng không dưới 70
                img.save(bio, format="JPEG", quality=current_quality, optimize=True)
        else:
            img.save(bio, format="JPEG", quality=current_quality, optimize=True)
        
        return bio.getvalue()

    def capture_once(self):
        with mss() as sct:
            # Lấy màn hình đầu tiên
            monitor = sct.monitors[1] # Thường là monitors[1] trên Windows/mss
            sct_img = sct.grab(monitor)
            
            # Convert sang PIL Image cực nhanh
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            return self._resize_if_needed(img)

        # img = pyautogui.screenshot()
        # return self._resize_if_needed(img)

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
    
    def set_mode(self, mode):
        """Đặt chế độ capture: VIEW, CONTROL, hoặc IDLE"""
        with self._lock:
            old_mode = self.mode
            self.mode = mode
            
            # Cập nhật FPS dựa trên mode
            if mode == self.MODE_VIEW:
                self.fps = self.fps_view  # 3 giây/frame
                print(f"[ClientScreenshot] 👁️ Chuyển sang VIEW mode (3s/frame)")
            elif mode == self.MODE_CONTROL:
                self.fps = self.fps_control  # 30 FPS
                print(f"[ClientScreenshot] 🎮 Chuyển sang CONTROL mode (30 FPS - continuous)")
            elif mode == self.MODE_IDLE:
                print(f"[ClientScreenshot] 💤 Chuyển sang IDLE mode (không gửi)")
            
            # Force full frame khi chuyển mode
            if old_mode != mode:
                self._force_full = True

    def capture_loop(self, callback):
        print(f"[ClientScreenshot] Bắt đầu capture loop (Hybrid Mode: Full + Rect)...")

        while not self.stop:
            # Cập nhật interval dựa trên mode hiện tại
            with self._lock:
                current_mode = self.mode
                current_fps = self.fps
            
            interval = 1.0 / current_fps if current_fps > 0 else 1.0
            
            # Nếu đang ở chế độ IDLE, bỏ qua capture và chờ
            if current_mode == self.MODE_IDLE:
                time.sleep(0.5)
                continue
            
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