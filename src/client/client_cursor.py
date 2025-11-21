# client/client_cursor.py

import threading
import time
import pyautogui
from typing import Optional, Tuple

class ClientCursorTracker(threading.Thread):
    """
    Theo dõi vị trí con trỏ chuột và gửi PDU Cursor khi có thay đổi.
    """
    
    def __init__(self, network, fps: int = 15, logger=None):
        super().__init__(daemon=True, name="CursorTracker")
        self.network = network
        self.fps = fps
        self.logger = logger or print
        self.running = False
        
        try:
            self.screen_width, self.screen_height = pyautogui.size()
        except Exception:
            self.screen_width, self.screen_height = 1920, 1080

        self.last_norm_pos: Tuple[float, float] = (0.0, 0.0)
        self.last_cursor_shape: Optional[bytes] = None # Dữ liệu hình dạng con trỏ (nếu có)

    def run(self):
        self.running = True
        interval = 1.0 / self.fps
        self.logger(f"[CursorTracker] Đã khởi động, FPS: {self.fps}")
        
        while self.running:
            start_time = time.perf_counter()
            
            try:
                # 1. Lấy vị trí chuột
                x, y = pyautogui.position()
                
                # 2. Chuẩn hóa vị trí (0.0 đến 1.0)
                # Đảm bảo không vượt quá biên 
                x_norm = max(0.0, min(1.0, x / self.screen_width))
                y_norm = max(0.0, min(1.0, y / self.screen_height))
                
                new_pos = (x_norm, y_norm)
                
                # 3. Kiểm tra thay đổi (ví dụ: thay đổi > 0.1% màn hình)
                if abs(new_pos[0] - self.last_norm_pos[0]) > 0.005 or \
                   abs(new_pos[1] - self.last_norm_pos[1]) > 0.005: 

                    # 4. Gửi PDU Cursor (shape_bytes = None)
                    self.network.send_cursor_pdu(x_norm, y_norm, cursor_shape_bytes=None)
                    self.last_norm_pos = new_pos
                    print(f"[CursorTracker] Gửi vị trí: {x_norm:.2f}, {y_norm:.2f}")

            except Exception as e:
                if self.running:
                    self.logger(f"[CursorTracker] Lỗi theo dõi chuột: {e}")

            elapsed = time.perf_counter() - start_time
            time.sleep(max(0, interval - elapsed))

    def stop(self):
        self.running = False