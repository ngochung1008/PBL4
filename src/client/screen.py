import socket
import struct
import time
import io
from mss import mss
from PIL import Image

SERVER_HOST = "10.10.30.11"  # thay bằng IP của máy giám sát
SERVER_PORT = 5000
FPS = 1  # số ảnh / giây (thay đổi theo nhu cầu)

def capture_jpeg_bytes(monitor_index=0, quality=70):
    with mss() as sct:
        monitor = sct.monitors[monitor_index]  # 0 = toàn màn hình
        sct_img = sct.grab(monitor)
        img = Image.frombytes("RGB", sct_img.size, sct_img.rgb)
        bio = io.BytesIO()
        img.save(bio, format="JPEG", quality=quality)
        data = bio.getvalue()
        return data

def send_loop(server_host, server_port, fps=1):
    interval = 1.0 / fps
    while True:
        try:
            print(f"Connecting to {server_host}:{server_port} ...")
            with socket.create_connection((server_host, server_port)) as s:
                print("Connected. Start sending screenshots.")
                while True:
                    start = time.time()
                    jpg = capture_jpeg_bytes(monitor_index=0, quality=60)
                    length = struct.pack(">I", len(jpg))
                    s.sendall(length + jpg)
                    elapsed = time.time() - start
                    to_sleep = max(0, interval - elapsed)
                    time.sleep(to_sleep)
        except Exception as e:
            print("Connection error:", e)
            print("Retrying in 5s...")
            time.sleep(5)

if __name__ == "__main__":
    send_loop(SERVER_HOST, SERVER_PORT, FPS)