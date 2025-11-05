# -*- coding: utf-8 -*-
import socket
import struct
import time
import threading
from queue import Queue

TPKT_HEADER_FMT = ">BBH"
MAX_TPKT_LENGTH = 65535
TPKT_OVERHEAD = 4


class ClientScreenSender:
    def __init__(self, server_host, server_port, client_id):
        self.server_host = server_host
        self.server_port = server_port
        self.client_id = client_id
        self.sequence = 0
        self.frame_queue = Queue(maxsize=1)
        self.stop_event = threading.Event()

    def enqueue_frame(self, width, height, jpg_bytes):
        """Đưa frame vào hàng đợi để gửi"""
        frame_header = struct.pack(">III", width, height, len(jpg_bytes))
        payload = frame_header + jpg_bytes
        if self.frame_queue.full():
            try:
                self.frame_queue.get_nowait()
            except:
                pass
        self.frame_queue.put(payload)

    def send_tpkt(self, sock, payload_bytes):
        """Gửi dữ liệu dạng TPKT"""
        total_len = TPKT_OVERHEAD + len(payload_bytes)
        if total_len > MAX_TPKT_LENGTH:
            print("[CLIENT] Frame quá lớn, bỏ qua:", len(payload_bytes))
            return
        tpkt = struct.pack(TPKT_HEADER_FMT, 0x03, 0x00, total_len)
        sock.sendall(tpkt + payload_bytes)

    def send_loop(self):
        """Kết nối và gửi liên tục các frame trong hàng đợi"""
        while not self.stop_event.is_set():
            try:
                print(f"[CLIENT] Đang kết nối đến {self.server_host}:{self.server_port} ...")
                sock = socket.create_connection((self.server_host, self.server_port), timeout=10)
                sock.sendall(("CLIENT:" + self.client_id).encode('utf-8'))
                print(f"[CLIENT] Đã handshake, id={self.client_id}")
                time.sleep(0.05)

                while not self.stop_event.is_set():
                    try:
                        payload = self.frame_queue.get(timeout=1)
                        self.send_tpkt(sock, payload)
                        self.sequence += 1
                        print(f"[CLIENT] Gửi seq={self.sequence} payload={len(payload)} bytes")
                    except Exception:
                        pass
            except Exception as e:
                print("[CLIENT] Lỗi:", e, "→ thử lại sau 5s")
                try:
                    sock.close()
                except:
                    pass
                time.sleep(5)