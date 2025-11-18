import threading
import time
import os
import sys

# Đổi các import
from client.client_network.client_network import ClientNetwork
from client.client_network.client_sender import ClientSender
from client.client_screenshot import ClientScreenshot
from client.client_input import ClientInputHandler
from client.client_constants import CLIENT_ID, CA_FILE

class Client:
    """
    Lớp "keo" (glue) cấp cao nhất.
    Khởi tạo và kết nối tất cả các thành phần.
    """
    def __init__(self, host, port, fps=2, logger=None):
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
        self.screenshot = ClientScreenshot(fps=fps, quality=75, max_dimension=1280)
        self.sender = ClientSender(self.network) # Truyền network
        self.input_handler = ClientInputHandler(logger=self.logger)
        
        self.screenshot_thread = None

        # --- Kết nối (Wire) các callback ---
        
        # Network nhận PDU -> gọi Input Handler
        self.network.on_input_pdu = self.input_handler.handle_input_pdu
        
        # Network nhận PDU -> gọi Control Handler (của lớp này)
        self.network.on_control_pdu = self._on_control_pdu
        
        # Network nhận PDU (ACK/NAK) -> gọi Sender
        self.network.on_file_ack = self.sender.handle_file_ack
        self.network.on_file_nak = self.sender.handle_file_nak
        
        # Network báo ngắt kết nối -> gọi hàm (của lớp này)
        self.network.on_disconnected = self._on_disconnected

    def start(self):
        """Khởi động network và các luồng"""
        self.logger("[Client] Đang khởi động...")
        
        # Khởi động Network (Connect, TLS, Receiver, PDU loop)
        if not self.network.start():
            self.logger("[Client] Không thể kết nối tới server.")
            return False
            
        # Khởi động Sender (Frame loop, Resend loop)
        self.sender.start()
        
        # Khởi động Screenshot
        self.screenshot.stop = False
        self.screenshot_thread = threading.Thread(
            target=self.screenshot.capture_loop, 
            args=(self._on_frame,), # Callback là _on_frame
            daemon=True
        )
        self.screenshot_thread.start()
        self.logger("[Client] Đã khởi động.")
        return True

    def stop(self):
        self.logger("[Client] Đang dừng...")
        self.screenshot.stop = True
        self.sender.stop()
        self.network.stop() # Sẽ kích hoạt _on_disconnected
        if self.screenshot_thread:
            self.screenshot_thread.join(timeout=1.0)
        self.logger("[Client] Đã dừng.")

    def _on_frame(self, width, height, jpg_bytes, bbox, img, seq, ts_ms):
        """
        Callback từ ClientScreenshot.
        Gửi frame vào hàng đợi của ClientSender.
        """
        # img không cần thiết, bỏ qua
        self.sender.enqueue_frame(width, height, jpg_bytes, bbox, seq, ts_ms)

    def _on_control_pdu(self, pdu: dict):
        """Xử lý PDU control từ server"""
        msg = pdu.get("message", "")
        self.logger(f"[Client] Nhận lệnh từ Server: {msg}")
        # TODO: Xử lý các lệnh (ví dụ: yêu cầu gửi file,...)
        
    def _on_disconnected(self):
        """Callback từ ClientNetwork khi mất kết nối"""
        self.logger("[Client] _on_disconnected được gọi.")
        # Dọn dẹp các luồng phụ (Sender, Screenshot)
        self.screenshot.stop = True
        self.sender.stop()
        if self.screenshot_thread:
            self.screenshot_thread.join(timeout=1.0)
            self.screenshot_thread = None


if __name__ == "__main__":
    """
    Main loop - Xử lý tự động kết nối lại (Auto-Reconnect)
    """
    host = "10.10.58.15" # Đổi thành IP server của bạn
    port = 3389
    
    # Tạo vòng lặp để tự động kết nối lại
    while True:
        client = None
        try:
            client = Client(host, port, fps=2)
            
            # Hàm start() sẽ block cho đến khi kết nối thành công
            if client.start():
                # Giữ luồng chính sống sót trong khi network đang chạy
                while client.network.running:
                    time.sleep(1)
            
            # Nếu client.start() thất bại, hoặc vòng lặp trên kết thúc
            # (do mất kết nối), code sẽ chạy xuống đây.
            
        except KeyboardInterrupt:
            if client:
                client.stop()
            break # Thoát vòng lặp while True
        except Exception as e:
            print(f"Lỗi nghiêm trọng: {e}")
            if client:
                client.stop()

        print("Mất kết nối. Thử kết nối lại sau 5 giây...")
        time.sleep(5)