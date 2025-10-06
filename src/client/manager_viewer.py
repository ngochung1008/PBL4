# manager_viewer.py 

import socket
import struct
import io
from PIL import Image
import matplotlib.pyplot as plt

class ManagerViewer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.running = True  # trạng thái vòng lặp

    def on_key(self, event):
        """Xử lý phím nhấn từ matplotlib"""
        if event.key == 'q':  # nhấn Q để thoát
            print("[MANAGER VIEWER] Quit signal received (q).")
            self.running = False
            plt.close()

    def run(self):
        """Nhận ảnh màn hình từ server và hiển thị"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((self.host, self.port))   # 🔥 kết nối tới server, KHÔNG bind
            sock.sendall(b"MGR:")   # 🔥 báo cho server biết đây là Manager
            print("[MANAGER VIEWER] Connected to server for screen stream")

            fig, ax = plt.subplots()
            fig.canvas.mpl_connect("key_press_event", self.on_key)
            img_disp = None

            while self.running:
                try:
                    # Đọc 4 byte độ dài
                    length_bytes = sock.recv(4)
                    if not length_bytes:
                        break
                    length = struct.unpack(">I", length_bytes)[0]

                    # Nhận dữ liệu ảnh
                    data = b""
                    while len(data) < length:
                        packet = sock.recv(length - len(data))
                        if not packet:
                            break
                        data += packet

                    if not data:
                        break

                    # Giải mã ảnh
                    jpg_stream = io.BytesIO(data)
                    img = Image.open(jpg_stream)

                    # Hiển thị
                    if img_disp is None:
                        img_disp = ax.imshow(img)
                        plt.axis("off")
                    else:
                        img_disp.set_data(img)

                    plt.pause(0.001)

                except Exception as e:
                    print("[MANAGER VIEWER] Error:", e)
                    break

            print("[MANAGER VIEWER] Closed connection.")