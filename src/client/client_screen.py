# client_screen.py
# -*- coding: utf-8 -*-
from __future__ import print_function
import socket
import struct
import time
import io
from mss import mss
from PIL import Image

# ==== Fix tương thích Pillow mới (>=10.0) ====
try:
    RESAMPLE_MODE = Image.Resampling.LANCZOS
except AttributeError:
    RESAMPLE_MODE = Image.ANTIALIAS

# ==== Định dạng gói RDP mô phỏng ====
TPKT_HEADER_FMT = ">BBH"  # version(1), reserved(1), length(2)
MAX_TPKT_LENGTH = 65535
TPKT_OVERHEAD = 4
FRAME_HEADER_SIZE = 12  # width(4), height(4), img_size(4)
MAX_PAYLOAD = MAX_TPKT_LENGTH - TPKT_OVERHEAD


class ClientScreenSender(object):
    def __init__(self, server_host, server_port, client_id, fps=2, quality=60, max_dimension=None):
        """
        Mô phỏng client RDP gửi khung hình đến server trung gian.
        max_dimension: nếu đặt, sẽ giảm kích thước ảnh về giới hạn này khi cần.
        """
        self.server_host = server_host
        self.server_port = server_port
        self.client_id = client_id
        self.fps = fps
        self.quality = quality
        self.sequence = 0
        self.max_dimension = max_dimension

    def capture_frame(self):
        """Chụp toàn màn hình và trả về ảnh PIL."""
        with mss() as sct:
            monitor = sct.monitors[0]
            sct_img = sct.grab(monitor)
            img = Image.frombytes("RGB", sct_img.size, sct_img.rgb)
            return img, sct_img.width, sct_img.height

    def resize_if_needed(self, img, target_bytes):
        """
        Giảm kích thước ảnh (bằng cách giảm chất lượng hoặc scale nhỏ dần)
        cho đến khi vừa giới hạn bytes.
        """
        q = self.quality
        # Giảm chất lượng trước
        while q >= 30:
            bio = io.BytesIO()
            img.save(bio, format="JPEG", quality=q)
            data = bio.getvalue()
            if len(data) <= target_bytes:
                return data, img.size
            q -= 10

        # Sau đó giảm kích thước
        w, h = img.size
        scale = 0.9
        while True:
            new_w = int(w * scale)
            new_h = int(h * scale)
            if new_w < 1 or new_h < 1:
                break
            img2 = img.resize((new_w, new_h), RESAMPLE_MODE)
            bio = io.BytesIO()
            img2.save(bio, format="JPEG", quality=max(20, q))
            data = bio.getvalue()
            if len(data) <= target_bytes:
                return data, (new_w, new_h)
            scale *= 0.9

        # fallback (trường hợp cực hạn)
        bio = io.BytesIO()
        img.resize((max(1, int(w * 0.1)), max(1, int(h * 0.1))), RESAMPLE_MODE).save(
            bio, format="JPEG", quality=20
        )
        return bio.getvalue(), img.size

    def send_tpkt(self, sock, payload_bytes):
        """Đóng gói và gửi theo định dạng TPKT."""
        total_len = TPKT_OVERHEAD + len(payload_bytes)
        if total_len > MAX_TPKT_LENGTH:
            raise ValueError("Payload too large for single TPKT: {}".format(total_len))
        tpkt = struct.pack(TPKT_HEADER_FMT, 0x03, 0x00, total_len)
        sock.sendall(tpkt + payload_bytes)

    def run(self):
        interval = 1.0 / float(self.fps)
        while True:
            try:
                print("[CLIENT] Connecting to {}:{} ...".format(self.server_host, self.server_port))
                sock = socket.create_connection((self.server_host, self.server_port), timeout=10)

                # === Handshake ===
                msg = "CLIENT:" + self.client_id
                sock.sendall(msg.encode('utf-8'))
                print("[CLIENT] Handshake sent, id={}".format(self.client_id))
                time.sleep(0.05)

                while True:
                    start = time.time()
                    img, w, h = self.capture_frame()

                    # === Nén ảnh JPEG ===
                    bio = io.BytesIO()
                    img.save(bio, format="JPEG", quality=self.quality)
                    jpg = bio.getvalue()

                    max_image_bytes = MAX_PAYLOAD - FRAME_HEADER_SIZE
                    if len(jpg) > max_image_bytes:
                        jpg, (w, h) = self.resize_if_needed(img, max_image_bytes)

                    frame_header = struct.pack(">III", int(w), int(h), len(jpg))
                    payload = frame_header + jpg

                    if len(payload) > MAX_PAYLOAD:
                        print("[CLIENT] Warning: frame too large ({} bytes), skipped.".format(len(payload)))
                    else:
                        self.send_tpkt(sock, payload)
                        self.sequence += 1
                        print("[CLIENT] Sent seq={} size={} bytes".format(self.sequence, len(payload)))

                    elapsed = time.time() - start
                    time.sleep(max(0, interval - elapsed))

            except KeyboardInterrupt:
                print("\n[CLIENT] Stopped by user.")
                try:
                    sock.close()
                except:
                    pass
                break
            except Exception as e:
                print("[CLIENT] Error:", e, "-> reconnect in 5s")
                try:
                    sock.close()
                except:
                    pass
                time.sleep(5)
