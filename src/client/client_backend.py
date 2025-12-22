"""
Client Backend - Core Logic Without GUI
"""

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

from src.client.client_network.client_network import ClientNetwork
from src.client.client_network.client_sender import ClientSender
from src.client.client_screenshot import ClientScreenshot
from src.client.client_input import ClientInputHandler
from src.client.client_cursor import ClientCursorTracker
from src.client.client_constants import CLIENT_ID, CA_FILE
from src.client.client_file_transfer import ClientFileTransfer


class ClientBackend:
    """
    Backend logic for client - handles networking, screenshots, monitoring
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
        self.sender = ClientSender(self.network)
        self.input_handler = ClientInputHandler(logger=self.logger)
        self.cursor_tracker = ClientCursorTracker(self.network, fps=30, logger=self.logger)
        
        # File Transfer
        self.file_transfer = ClientFileTransfer(self.sender, None)
        self._setup_file_transfer_callbacks()

        self.screenshot_thread = None
        self.monitor_thread = None
        self.last_full_frame_ts = 0
        self.full_frame_interval = 30 
        
        # Track session state
        self.in_session = False
        self.viewer_count = 0      # Số lượng managers đang xem
        self.is_being_controlled = False  # Có manager đang điều khiển không

        # Kết nối các callback
        self.network.on_input_pdu = self.input_handler.handle_input_pdu
        self.network.on_control_pdu = self._on_control_pdu
        self.network.on_file_pdu = self._on_file_pdu
        self.network.on_file_ack = self.sender.handle_file_ack
        self.network.on_file_nak = self.sender.handle_file_nak
        self.network.on_disconnected = self._on_disconnected

    def start(self):
        """Khởi động network và các luồng"""
        self.logger("[ClientBackend] Đang khởi động...")
        
        # 1. Khởi động Network
        if not self.network.start():
            self.logger("[ClientBackend] Không thể kết nối tới server.")
            return False
            
        # 2. Login với server
        self._login_to_server()
        
        # 2.5. Bắt đầu capture ngay sau khi login (VIEW mode)
        self.logger("[ClientBackend] 📸 Bắt đầu capture màn hình tự động...")
        self.screenshot.set_mode(ClientScreenshot.MODE_VIEW)
        
        # 3. Khởi động Sender
        self.sender.start()
        
        # 4. Khởi động Screenshot
        self.screenshot.stop = False
        self.screenshot.force_full_frame()
        self.last_full_frame_ts = time.time()
        
        self.screenshot_thread = threading.Thread(
            target=self.screenshot.capture_loop, 
            args=(self._on_frame,),
            daemon=True
        )
        self.screenshot_thread.start()
        
        # 5. Khởi động Cursor Tracker
        self.cursor_tracker.start()

        # 6. Khởi động Luồng Giám sát (Security Monitor)
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True
        )
        self.monitor_thread.start()

        self.logger("[ClientBackend] Đã khởi động toàn bộ dịch vụ.")
        return True

    def _login_to_server(self):
        """Login với server để được authenticate"""
        self.logger("[ClientBackend] Đang đăng nhập với server...")
        login_cmd = f"login:client:client:client"
        self.network.send_control_pdu(login_cmd)

    def stop(self):
        self.logger("[ClientBackend] Đang dừng...")
        self.screenshot.stop = True
        self.cursor_tracker.stop()
        self.sender.stop()
        self.network.stop()
        
        if self.screenshot_thread:
            self.screenshot_thread.join(timeout=1.0)
            
        self.logger("[ClientBackend] Đã dừng.")
    
    def _update_screenshot_mode(self):
        """
        Cập nhật chế độ screenshot dựa trên session hiện tại:
        - Nếu đang bị control: CONTROL mode (30 FPS - continuous)
        - Ngược lại: LUÔN VIEW mode (2s/frame) - để server lưu screenshots thường xuyên
        """
        print(f"[ClientBackend] _update_screenshot_mode: is_being_controlled={self.is_being_controlled}, viewer_count={self.viewer_count}")
        if self.is_being_controlled:
            # Ưu tiên CONTROL mode (mượt mà, liên tục - 30 FPS)
            self.screenshot.set_mode(self.screenshot.MODE_CONTROL)
            self.in_session = True
            print(f"[ClientBackend] ✅ Set CONTROL mode (30 FPS)")
        else:
            # LUÔN BẬT VIEW MODE - Không bao giờ IDLE
            # Server cần screenshots liên tục để giám sát và lưu lại
            self.screenshot.set_mode(self.screenshot.MODE_VIEW)
            self.in_session = True
            print(f"[ClientBackend] ✅ Set VIEW mode (2s/frame) - Auto capture ON")

    def _monitor_loop(self):
        """Giám sát cửa sổ active và phát hiện vi phạm"""
        self.logger("[Monitor] Đã bật chế độ giám sát nội dung cửa sổ...")
        last_title_sent = ""
        
        # Danh sách từ khóa đen (Blacklist)
        blacklist_keywords = [
            "phimmoi", "phim hay",
            "bet88", "w88", "cá cược", "nhà cái",
            "xoilac", "trực tiếp bóng đá",
            "sex", "18+"
        ]

        while self.network.running:
            try:
                active_window = gw.getActiveWindow()
                
                if active_window:
                    title = active_window.title.lower()
                    
                    is_violation = False
                    detected_word = ""
                    
                    for bad_word in blacklist_keywords:
                        if bad_word in title:
                            is_violation = True
                            detected_word = bad_word
                            break
                    
                    if is_violation and title != last_title_sent:
                        self.logger(f"[Monitor] !!! PHÁT HIỆN VI PHẠM: {title}")
                        
                        msg = f"security_alert:Web Cấm ({detected_word})|Đang truy cập: {active_window.title}"
                        self.network.send_control_pdu(msg)
                        
                        last_title_sent = title
                        
            except Exception:
                pass
            
            time.sleep(2)

    def _on_frame(self, width, height, jpg_bytes, bbox, img, seq, ts_ms):
        # LUÔN GỬI FRAMES - Không cần kiểm tra session
        # Server sẽ tự động lưu screenshots
        # print(f"[ClientBackend] _on_frame: size={len(jpg_bytes)}, seq={seq}")
        result = self.sender.enqueue_frame(width, height, jpg_bytes, bbox, seq, ts_ms)
        return result

    def _on_control_pdu(self, pdu: dict):
        msg = pdu.get("message", "")
        self.logger(f"[ClientBackend] Nhận lệnh từ Server: {msg}")
        
        # === Xử lý VIEW SESSION ===
        if msg.startswith("view_started"):
            # Format: "view_started:manager_id"
            manager_id = msg.split(":")[1] if ":" in msg else "Manager"
            self.viewer_count += 1
            self.logger(f"[ClientBackend] 👁️ Manager {manager_id} đã bắt đầu xem. Tổng viewers: {self.viewer_count}")
            self._update_screenshot_mode()
            self.screenshot.force_full_frame()
            
        elif msg.startswith("view_stopped"):
            # Format: "view_stopped:manager_id"
            manager_id = msg.split(":")[1] if ":" in msg else "Manager"
            self.viewer_count = max(0, self.viewer_count - 1)
            self.logger(f"[ClientBackend] 👁️ Manager {manager_id} đã dừng xem. Còn lại: {self.viewer_count}")
            self._update_screenshot_mode()
        
        # === Xử lý CONTROL SESSION ===
        elif msg.startswith("control_started"):
            # Format: "control_started:manager_id"
            manager_id = msg.split(":")[1] if ":" in msg else "Manager"
            self.is_being_controlled = True
            self.logger(f"[ClientBackend] 🎮 Manager {manager_id} đã bắt đầu điều khiển!")
            self._update_screenshot_mode()
            self.screenshot.force_full_frame()
            
        elif msg.startswith("control_stopped"):
            # Format: "control_stopped:manager_id"
            print(f"[ClientBackend] 🎮 Received CONTROL_STOPPED: {msg}")
            manager_id = msg.split(":")[1] if ":" in msg else "Manager"
            self.is_being_controlled = False
            self.logger(f"[ClientBackend] 🎮 Manager {manager_id} đã dừng điều khiển.")
            self._update_screenshot_mode()
            print(f"[ClientBackend] ✅ Control stopped processed, is_being_controlled={self.is_being_controlled}, viewer_count={self.viewer_count}")
        
        # === Xử lý LEGACY SESSION (deprecated) ===
        elif msg.startswith("session_started"):
            manager_id = msg.split(":")[1] if ":" in msg else "Manager"
            self.logger(f"[ClientBackend] ==> Manager {manager_id} đã kết nối! Bắt đầu gửi video.")
            self.in_session = True
            self.screenshot.force_full_frame()
            
        elif msg == "session_ended":
            self.logger("[ClientBackend] Session ended")
            self.in_session = False
            
        elif msg == "request_refresh":
            if self.in_session:
                self.screenshot.force_full_frame()
        
        # === Xử lý FILE TRANSFER COMMANDS ===
        elif msg.startswith("file_transfer_start"):
            # Format: "file_transfer_start:transfer_id"
            self.file_transfer.handle_file_transfer_ack(msg)
        elif msg.startswith("file_transfer_ack"):
            # Format: "file_transfer_ack:chunk_num"
            self.file_transfer.handle_file_transfer_ack(msg)
        elif msg.startswith("file_transfer_complete"):
            # Format: "file_transfer_complete:transfer_id"
            self.file_transfer.handle_file_received(msg)
        elif msg.startswith("file_transfer_error"):
            # Format: "file_transfer_error:error_message"
            self.logger(f"[ClientBackend] File transfer error: {msg}")
    
    def _on_file_pdu(self, pdu: dict):
        """Xử lý FILE PDU từ server"""
        self.file_transfer.handle_file_pdu(pdu)
    
    def _setup_file_transfer_callbacks(self):
        """Setup file transfer callbacks"""
        # Progress callback
        def on_progress(progress):
            self.logger(f"[ClientBackend] File send progress: {progress}%")
        
        # Complete callback
        def on_complete():
            self.logger("[ClientBackend] File send complete!")
        
        # Error callback
        def on_error(error_msg):
            self.logger(f"[ClientBackend] File send error: {error_msg}")
        
        # Received file callback
        def on_file_received(filename, filepath):
            self.logger(f"[ClientBackend] File received: {filename} at {filepath}")
        
        self.file_transfer.on_progress = on_progress
        self.file_transfer.on_complete = on_complete
        self.file_transfer.on_error = on_error
        self.file_transfer.on_file_received = on_file_received
    
    def gui_send_file(self, target_id: str, filepath: str):
        """GUI calls this to send file"""
        self.logger(f"[ClientBackend] Sending file to {target_id}: {filepath}")
        self.file_transfer.send_file(target_id, filepath)
        
    def _on_disconnected(self):
        self.logger("[ClientBackend] _on_disconnected được gọi.")
        self.screenshot.stop = True
        self.cursor_tracker.stop()
        self.sender.stop()
        if self.screenshot_thread:
            self.screenshot_thread.join(timeout=1.0)
            self.screenshot_thread = None


if __name__ == "__main__":
    """
    Entry point - Run Client with GUI
    """
    import socket
    from PyQt6.QtWidgets import QApplication
    from src.client.gui.main_window import ClientMainWindow
    
    def get_local_ip():
        """Lấy địa chỉ IP local của máy"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "Unknown"
    
    # Khởi tạo Qt Application
    app = QApplication(sys.argv)
    app.setApplicationName("Remote Control Client")
    
    # Tạo và hiển thị main window
    main_window = ClientMainWindow()
    main_window.show()
    
    print(f"[Client] Local IP: {get_local_ip()}")
    print("[Client] GUI started. Use the interface to connect to server.")
    
    # Chạy event loop
    sys.exit(app.exec())
