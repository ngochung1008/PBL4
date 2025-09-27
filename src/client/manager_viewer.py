import socket
import struct
import io
from PIL import Image
import matplotlib.pyplot as plt

class ManagerViewer:
    def __init__(self, host, port):
        self.host = host
        self.port = port

    def run(self):
        """Nhận ảnh màn hình từ client và hiển thị"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind((self.host, self.port))
            sock.listen(1)
            print("[MANAGER VIEWER] Waiting for client screen...")
            conn, addr = sock.accept()
            print("[MANAGER VIEWER] Client connected:", addr)

            fig, ax = plt.subplots()
            img_disp = None

            while True:
                length_bytes = conn.recv(4)
                if not length_bytes:
                    break
                length = struct.unpack(">I", length_bytes)[0]

                data = b""
                while len(data) < length:
                    packet = conn.recv(length - len(data))
                    if not packet:
                        break
                    data += packet

                jpg_stream = io.BytesIO(data)
                img = Image.open(jpg_stream)

                if img_disp is None:
                    img_disp = ax.imshow(img)
                else:
                    img_disp.set_data(img)

                plt.pause(0.001)