# client_screen.py

import socket
import struct
import time
import io
from mss import mss
from PIL import Image

class ClientScreen:
    def __init__(self, server_host, screen_port, fps=15, quality=70):
        self.server_host = server_host
        self.screen_port = screen_port
        self.fps = fps # tốc độ khung hình 
        self.quality = quality # chất lượng nén JPEG (1-100)

    def capture_frame(self):
        with mss() as sct:
            # Sử dụng thư viện mss để chụp toàn bộ màn hình (sct.monitors[0]).
            monitor = sct.monitors[0]  
            sct_img = sct.grab(monitor) 
            img = Image.frombytes("RGB", sct_img.size, sct_img.rgb) # Chuyển đổi sang đối tượng PIL Image
            return img, sct_img.width, sct_img.height

    def run(self):
        interval = 1.0 / self.fps

        # Vòng lặp ngoài: Xử lý kết nối lại khi mất kết nối
        while True:
            try:
                with socket.create_connection((self.server_host, self.screen_port), timeout=10) as s:
                    s.sendall(b"CLNT:") # Gửi mã định danh Client (handshake) lên Server
                    print("[CLIENT SCREEN] Connected to server for screen. Starting stream.")
                    
                    # Vòng lặp trong: Truyền frame liên tục
                    while True:
                        start = time.time()

                        # 1. Chụp màn hình
                        img, w, h = self.capture_frame()

                        # 2. Nén ảnh sang JPEG
                        bio = io.BytesIO()
                        img.save(bio, format="JPEG", quality=self.quality)
                        jpg = bio.getvalue()

                        # 3. Gửi ảnh đã nén lên Server với header (width, height, length)
                        header = struct.pack(">III", w, h, len(jpg))

                        # debug log
                        print(f"[CLIENT SCREEN] Sending frame {w}x{h}, {len(jpg)} bytes")
                        
                        # 4. Gửi dữ liệu qua socket
                        s.sendall(header + jpg)

                        # 5. Chờ để duy trì tốc độ khung hình
                        elapsed = time.time() - start
                        time.sleep(max(0, interval - elapsed))
            except socket.timeout:
                print("[CLIENT SCREEN] Connection attempt timed out.")
            except ConnectionRefusedError:
                print("[CLIENT SCREEN] Connection refused. Is server running?")
            except Exception as e:
                # Xử lý lỗi chung (socket disconnect, mss error, etc.)
                print(f"[CLIENT SCREEN] Unexpected Error: {e}. Retrying in 5s.")
            
            time.sleep(5) # Đợi 5 giây trước khi thử kết nối lại