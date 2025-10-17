import socket
import struct
import time
import io
from mss import mss
from PIL import Image

class ClientScreen:
    def __init__(self, server_host, screen_port, fps=1, quality=60):
        self.server_host = server_host
        self.screen_port = screen_port
        self.fps = fps
        self.quality = quality

    def capture_frame(self):
        with mss() as sct:
            monitor = sct.monitors[0]  # full screen
            sct_img = sct.grab(monitor)
            img = Image.frombytes("RGB", sct_img.size, sct_img.rgb)
            return img, sct_img.width, sct_img.height

    def run(self):
        interval = 1.0 / self.fps
        while True:
            try:
                with socket.create_connection((self.server_host, self.screen_port)) as s:
                    s.settimeout(5)  # <-- THÊM timeout 5 giây
                    s.sendall(b"CLNT:")
                    print("[CLIENT SCREEN] Connected to screen server as Client")

                    while True:
                        start = time.time()
                        img, w, h = self.capture_frame()

                        bio = io.BytesIO()
                        img.save(bio, format="JPEG", quality=self.quality)
                        jpg = bio.getvalue()

                        header = struct.pack(">III", w, h, len(jpg))
                        s.sendall(header + jpg)

                        elapsed = time.time() - start
                        time.sleep(max(0, interval - elapsed))
            except Exception as e:
                print("[CLIENT SCREEN] Error:", e)
                time.sleep(5)