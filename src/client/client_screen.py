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

    def capture_jpeg_bytes(self, monitor_index=0):
        with mss() as sct:
            monitor = sct.monitors[monitor_index]
            sct_img = sct.grab(monitor)
            img = Image.frombytes("RGB", sct_img.size, sct_img.rgb)
            bio = io.BytesIO()
            img.save(bio, format="JPEG", quality=self.quality)
            return bio.getvalue()

    def run(self):
        interval = 1.0 / self.fps
        while True:
            try:
                with socket.create_connection((self.server_host, self.screen_port)) as s:
                    print("[CLIENT SCREEN] Connected to screen server")
                    while True:
                        start = time.time()
                        jpg = self.capture_jpeg_bytes()
                        length = struct.pack(">I", len(jpg))
                        s.sendall(length + jpg)
                        elapsed = time.time() - start
                        time.sleep(max(0, interval - elapsed))
            except Exception as e:
                print("[CLIENT SCREEN] Error:", e)
                time.sleep(5)
