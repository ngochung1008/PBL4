# client_screen.py
# -*- coding: utf-8 -*-
from __future__ import print_function
import socket
import struct
import time
import io
from mss import mss
from PIL import Image

TPKT_HEADER_FMT = ">BBH"  # version(1), reserved(1), length(2)
MAX_TPKT_LENGTH = 65535
TPKT_OVERHEAD = 4
FRAME_HEADER_SIZE = 12  # width(4), height(4), img_size(4)
MAX_PAYLOAD = MAX_TPKT_LENGTH - TPKT_OVERHEAD  # max payload bytes in one TPKT

class ClientScreenSender(object):
    def __init__(self, server_host, server_port, client_id, fps=2, quality=60, max_dimension=None):
        """
        max_dimension: if set (int), will downscale long edge to this size when needed.
        """
        self.server_host = server_host
        self.server_port = server_port
        self.client_id = client_id
        self.fps = fps
        self.quality = quality
        self.sequence = 0
        self.max_dimension = max_dimension

    def capture_frame(self):
        with mss() as sct:
            monitor = sct.monitors[0]
            sct_img = sct.grab(monitor)
            img = Image.frombytes("RGB", sct_img.size, sct_img.rgb)
            return img, sct_img.width, sct_img.height

    def resize_if_needed(self, img, target_bytes):
        """
        Reduce image size (first by lowering quality, then by scaling down) until its JPEG bytes <= target_bytes.
        Returns bytes and (w,h).
        """
        # try reducing quality first (down to 30)
        q = self.quality
        while q >= 30:
            bio = io.BytesIO()
            img.save(bio, format="JPEG", quality=q)
            data = bio.getvalue()
            if len(data) <= target_bytes:
                return data, img.size
            q -= 10

        # then scale down progressively
        w, h = img.size
        scale = 0.9
        while True:
            new_w = int(w * scale)
            new_h = int(h * scale)
            if new_w < 1 or new_h < 1:
                break
            img2 = img.resize((new_w, new_h), Image.ANTIALIAS)
            bio = io.BytesIO()
            img2.save(bio, format="JPEG", quality=max(20, q))
            data = bio.getvalue()
            if len(data) <= target_bytes:
                return data, (new_w, new_h)
            scale *= 0.9  # reduce further

        # fallback: return whatever smallest we got
        bio = io.BytesIO()
        img.resize((max(1, int(w*0.1)), max(1, int(h*0.1))), Image.ANTIALIAS).save(bio, format="JPEG", quality=20)
        data = bio.getvalue()
        return data, img.size

    def send_tpkt(self, sock, payload_bytes):
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
                # Send handshake
                try:
                    sock.sendall(("CLIENT:" + self.client_id).encode('utf-8'))
                except:
                    sock.sendall("CLIENT:" + self.client_id)
                print("[CLIENT] Handshake sent, id={}".format(self.client_id))
                time.sleep(0.05)

                while True:
                    start = time.time()
                    img, w, h = self.capture_frame()
                    # prepare jpg; ensure fit into MAX_PAYLOAD minus frame header
                    max_image_bytes = MAX_PAYLOAD - FRAME_HEADER_SIZE
                    bio = io.BytesIO()
                    img.save(bio, format="JPEG", quality=self.quality)
                    jpg = bio.getvalue()

                    if len(jpg) > max_image_bytes:
                        # try to reduce until fits
                        jpg, (w2, h2) = self.resize_if_needed(img, max_image_bytes)
                        w, h = w2, h2

                    frame_header = struct.pack(">III", int(w), int(h), len(jpg))
                    payload = frame_header + jpg

                    # final safety check
                    if len(payload) > MAX_PAYLOAD:
                        print("[CLIENT] Warning: frame still too large ({} bytes). Skipping frame.".format(len(payload)))
                    else:
                        self.send_tpkt(sock, payload)
                        self.sequence += 1
                        print("[CLIENT] Sent seq={} size={} bytes (frame total {})".format(self.sequence, len(jpg), len(payload)))

                    elapsed = time.time() - start
                    time.sleep(max(0, interval - elapsed))
            except KeyboardInterrupt:
                print("\n[CLIENT] Exiting by user.")
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
