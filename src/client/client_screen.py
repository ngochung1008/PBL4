# -*- coding: utf-8 -*-
from __future__ import print_function
import socket
import struct
import time
import io
import threading
from queue import Queue
from mss import mss
from PIL import Image

try:
    RESAMPLE_MODE = Image.Resampling.LANCZOS
except AttributeError:
    RESAMPLE_MODE = Image.ANTIALIAS

TPKT_HEADER_FMT = ">BBH"
MAX_TPKT_LENGTH = 65535
TPKT_OVERHEAD = 4
FRAME_HEADER_SIZE = 12
MAX_PAYLOAD = MAX_TPKT_LENGTH - TPKT_OVERHEAD

class ClientScreenSender(object):
    def __init__(self, server_host, server_port, client_id, fps=2, quality=75, max_dimension=1280):
        self.server_host = server_host
        self.server_port = server_port
        self.client_id = client_id
        self.fps = fps
        self.quality = quality
        self.sequence = 0
        self.max_dimension = max_dimension
        self.frame_queue = Queue(maxsize=1)  # max 1 frame, drop old
        self.stop_event = threading.Event()

    def capture_loop(self):
        interval = 1.0 / self.fps
        with mss() as sct:
            monitor = sct.monitors[0]
            while not self.stop_event.is_set():
                start = time.time()
                sct_img = sct.grab(monitor)
                img = Image.frombytes("RGB", sct_img.size, sct_img.rgb)

                # Resize if max_dimension set
                w, h = img.size
                long_edge = max(w, h)
                if self.max_dimension and long_edge > self.max_dimension:
                    scale = float(self.max_dimension) / long_edge
                    new_w = int(w * scale)
                    new_h = int(h * scale)
                    img = img.resize((new_w, new_h), RESAMPLE_MODE)

                # Encode JPEG
                bio = io.BytesIO()
                img.save(bio, format="JPEG", quality=self.quality)
                jpg_bytes = bio.getvalue()

                # Build payload
                frame_header = struct.pack(">III", img.width, img.height, len(jpg_bytes))
                payload = frame_header + jpg_bytes

                # Put into queue, drop old if full
                if self.frame_queue.full():
                    try:
                        self.frame_queue.get_nowait()
                    except:
                        pass
                self.frame_queue.put(payload)

                elapsed = time.time() - start
                time.sleep(max(0, interval - elapsed))

    def send_tpkt(self, sock, payload_bytes):
        total_len = TPKT_OVERHEAD + len(payload_bytes)
        if total_len > MAX_TPKT_LENGTH:
            print("[CLIENT] Frame too big, skipping:", len(payload_bytes))
            return
        tpkt = struct.pack(TPKT_HEADER_FMT, 0x03, 0x00, total_len)
        sock.sendall(tpkt + payload_bytes)

    def send_loop(self):
        while not self.stop_event.is_set():
            try:
                print("[CLIENT] Connecting to {}:{} ...".format(self.server_host, self.server_port))
                sock = socket.create_connection((self.server_host, self.server_port), timeout=10)
                sock.sendall(("CLIENT:" + self.client_id).encode('utf-8'))
                print("[CLIENT] Handshake sent, id={}".format(self.client_id))
                time.sleep(0.05)

                while not self.stop_event.is_set():
                    try:
                        payload = self.frame_queue.get(timeout=1)
                        self.send_tpkt(sock, payload)
                        self.sequence += 1
                        print("[CLIENT] Sent seq={} payload_bytes={}".format(self.sequence, len(payload)))
                    except Exception:
                        pass

            except Exception as e:
                print("[CLIENT] Error:", e, "-> reconnect in 5s")
                try:
                    sock.close()
                except:
                    pass
                time.sleep(5)

    def run(self):
        t_capture = threading.Thread(target=self.capture_loop)
        t_capture.daemon = True
        t_capture.start()
        try:
            self.send_loop()
        except KeyboardInterrupt:
            print("[CLIENT] Stopped by user.")
            self.stop_event.set()
