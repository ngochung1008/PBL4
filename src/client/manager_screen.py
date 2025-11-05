# manager_screen.py
# -*- coding: utf-8 -*-
from __future__ import print_function
import socket
import struct
import cv2
import numpy as np
import time
import threading
from queue import Queue

TPKT_HEADER_FMT = ">BBH"

def recv_all(sock, n):
    data = b''
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            raise ConnectionError("Socket closed")
        data += chunk
    return data

class ManagerScreenReceiver(object):
    def __init__(self, server_host, server_port, target_client_id):
        self.server_host = server_host
        self.server_port = server_port
        self.target_client_id = target_client_id
        self.frame_queue = Queue(maxsize=1)
        self.stop_event = threading.Event()

    def recv_loop(self):
        while not self.stop_event.is_set():
            try:
                sock = socket.create_connection((self.server_host, self.server_port), timeout=10)
                sock.sendall(b"MANAGER")
                time.sleep(0.05)
                sock.sendall(("SUBSCRIBE:" + self.target_client_id).encode('utf-8'))
                print("[MANAGER] Subscribed to client:", self.target_client_id)

                while not self.stop_event.is_set():
                    hdr = recv_all(sock, 4)
                    ver, reserved, length = struct.unpack(TPKT_HEADER_FMT, hdr)
                    payload_len = length - 4
                    payload = recv_all(sock, payload_len)
                    if self.frame_queue.full():
                        try:
                            self.frame_queue.get_nowait()
                        except:
                            pass
                    self.frame_queue.put(payload)
            except Exception as e:
                print("[MANAGER] Error:", e, "-> reconnect in 5s")
                try:
                    sock.close()
                except:
                    pass
                time.sleep(5)

    def display_loop(self):
        while not self.stop_event.is_set():
            try:
                payload = self.frame_queue.get(timeout=1)
                if len(payload) < 12:
                    continue
                w, h, img_size = struct.unpack(">III", payload[:12])
                jpg_bytes = payload[12:]
                np_arr = np.frombuffer(jpg_bytes, np.uint8)
                frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                if frame is not None:
                    cv2.imshow("Remote - {}".format(self.target_client_id), frame)
                    key = cv2.waitKey(1)
                    if key == 27:  # ESC
                        self.stop_event.set()
                        break
            except Exception:
                pass
        cv2.destroyAllWindows()

    def run(self):
        t_recv = threading.Thread(target=self.recv_loop)
        t_recv.daemon = True
        t_recv.start()
        self.display_loop()
