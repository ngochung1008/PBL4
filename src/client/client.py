# client/client.py

import threading
import time
import os
import sys

# [THÊM] Thư viện lấy tiêu đề cửa sổ
try:
    import pygetwindow as gw
except ImportError:
    print("Lỗi: Thiếu thư viện 'pygetwindow'. Hãy chạy lệnh: pip install pygetwindow")
    sys.exit(1)

from client.client_network.client_network import ClientNetwork
from client.client_network.client_sender import ClientSender
from client.client_screenshot import ClientScreenshot
from client.client_input import ClientInputHandler
from client.client_cursor import ClientCursorTracker
from client.client_constants import CLIENT_ID, CA_FILE

class Client:
    """
    Lớp "keo" (glue) cấp cao nhất.
    Khởi tạo và kết nối tất cả các thành phần.
    """
    def __init__(self, host, port, fps=10, logger=None):
        self.host = host
        self.port = port
        self.fps = fps
        self.logger = logger or print
        
        # Kiểm tra file CA
        if not os.path.exists(CA_FILE):
            self.logger(f"Lỗi: Không tìm thấy file CA: '{CA_FILE}'")
            self.logger("Vui lòng sao chép 'server.crt' từ server về thư mục này và đổi tên thành 'ca.crt'.")
            sys.exit(1)
            
        # Khởi tạo các thành phần
        self.network = ClientNetwork(
            host, port, 
            client_id=CLIENT_ID, 
            cafile=CA_FILE, 
            logger=self.logger
        )
        self.screenshot = ClientScreenshot(fps=fps, quality=65, max_dimension=1280)
        self.sender = ClientSender(self.network) # Truyền network
        self.input_handler = ClientInputHandler(logger=self.logger)
        self.cursor_tracker = ClientCursorTracker(self.network, fps=30, logger=self.logger)

        self.screenshot_thread = None
        self.monitor_thread = None # [THÊM] Thread giám sát
        self.last_full_frame_ts = 0
        self.full_frame_interval = 30 

        # --- Kết nối (Wire) các callback ---
        self.network.on_input_pdu = self.input_handler.handle_input_pdu
        self.network.on_control_pdu = self._on_control_pdu
        self.network.on_file_ack = self.sender.handle_file_ack
        self.network.on_file_nak = self.sender.handle_file_nak
        self.network.on_disconnected = self._on_disconnected

    def start(self):
        """Khởi động network và các luồng"""
        self.logger("[Client] Đang khởi động...")
        
        # 1. Khởi động Network
        if not self.network.start():
            self.logger("[Client] Không thể kết nối tới server.")
            return False
            
        # 2. Khởi động Sender
        self.sender.start()
        
        # 3. Khởi động Screenshot
        self.screenshot.stop = False
        self.screenshot.force_full_frame()
        self.last_full_frame_ts = time.time()
        
        self.screenshot_thread = threading.Thread(
            target=self.screenshot.capture_loop, 
            args=(self._on_frame,),
            daemon=True
        )
        self.screenshot_thread.start()
        
        # 4. Khởi động Cursor Tracker
        self.cursor_tracker.start()

        # 5. [THÊM] Khởi động Luồng Giám sát (Security Monitor)
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True
        )
        self.monitor_thread.start()

        self.logger("[Client] Đã khởi động toàn bộ dịch vụ.")
        return True

    def stop(self):
        self.logger("[Client] Đang dừng...")
        self.screenshot.stop = True
        self.cursor_tracker.stop()
        self.sender.stop()
        self.network.stop() # Sẽ kích hoạt _on_disconnected
        
        if self.screenshot_thread:
            self.screenshot_thread.join(timeout=1.0)
        # Monitor thread là daemon nên sẽ tự tắt khi main thread tắt
            
        self.logger("[Client] Đã dừng.")

    # --- [THÊM] HÀM GIÁM SÁT CỬA SỔ ---
    def _monitor_loop(self):
        self.logger("[Monitor] Đã bật chế độ giám sát nội dung cửa sổ...")
        last_title_sent = ""
        
        # Danh sách từ khóa đen (Blacklist)
        # Bạn có thể thêm các từ khóa khác vào đây
        blacklist_keywords = [
            "phimmoi", "phim hay", # Web phim lậu
            "bet88", "w88", "cá cược", "nhà cái", # Web cá độ
            "xoilac", "trực tiếp bóng đá", # Web bóng đá lậu
            "sex", "18+" # Web đồi trụy
        ]

        while self.network.running:
            try:
                # Lấy cửa sổ đang active (cửa sổ người dùng đang xem)
                active_window = gw.getActiveWindow()
                
                if active_window:
                    title = active_window.title.lower()
                    
                    # Kiểm tra xem tiêu đề có chứa từ khóa cấm không
                    is_violation = False
                    detected_word = ""
                    
                    for bad_word in blacklist_keywords:
                        if bad_word in title:
                            is_violation = True
                            detected_word = bad_word
                            break
                    
                    # Nếu phát hiện vi phạm VÀ chưa gửi cảnh báo cho tiêu đề này
                    if is_violation and title != last_title_sent:
                        self.logger(f"[Monitor] !!! PHÁT HIỆN VI PHẠM: {title}")
                        
                        # Gửi lệnh CMD_SECURITY_ALERT lên Server
                        # Định dạng: "security_alert:Loại vi phạm|Chi tiết"
                        msg = f"security_alert:Web Cấm ({detected_word})|Đang truy cập: {active_window.title}"
                        self.network.send_control_pdu(msg)
                        
                        last_title_sent = title # Đánh dấu đã gửi để tránh spam
                        
            except Exception as e:
                # Đôi khi gw.getActiveWindow() bị lỗi permission hoặc ko lấy được handle
                pass
            
            # Kiểm tra mỗi 2 giây để không tốn CPU
            time.sleep(2)

    def _on_frame(self, width, height, jpg_bytes, bbox, img, seq, ts_ms):
        return self.sender.enqueue_frame(width, height, jpg_bytes, bbox, seq, ts_ms)

    def _on_control_pdu(self, pdu: dict):
        msg = pdu.get("message", "")
        self.logger(f"[Client] Nhận lệnh từ Server: {msg}")
        
        if msg.startswith("session_started"):
            manager_id = msg.split(":")[1] if ":" in msg else "Manager"
            self.logger(f"[Client] ==> Manager {manager_id} đã kết nối! Refresh frame.")
            self.screenshot.force_full_frame()
            
        elif msg == "request_refresh":
            self.screenshot.force_full_frame()
        
    def _on_disconnected(self):
        self.logger("[Client] _on_disconnected được gọi.")
        self.screenshot.stop = True
        self.cursor_tracker.stop()
        self.sender.stop()
        if self.screenshot_thread:
            self.screenshot_thread.join(timeout=1.0)
            self.screenshot_thread = None


if __name__ == "__main__":
    host = "10.10.59.122" # Đổi thành IP server của bạn
    port = 5000
    
    while True:
        client = None
        try:
            client = Client(host, port, fps=10) 
            # Cấu hình screenshot
            client.screenshot.detect_delta = True
            client.screenshot.quality = 65
            
            if client.start():
                while client.network.running:
                    time.sleep(1)
            
        except KeyboardInterrupt:
            if client: client.stop()
            break 
        except Exception as e:
            print(f"Lỗi nghiêm trọng: {e}")
            if client: client.stop()

        print("Mất kết nối. Thử kết nối lại sau 5 giây...")
        time.sleep(5)