# manager_screen.py
# -*- coding: utf-8 -*-
from __future__ import print_function
import socket
import struct
import cv2
import numpy as np

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

    def run(self):
        while True:
            try:
                print("[MANAGER] Connecting to {}:{} ...".format(self.server_host, self.server_port))
                sock = socket.create_connection((self.server_host, self.server_port))
                sock.sendall(b"MANAGER")
                sock.sendall(("SUBSCRIBE:" + self.target_client_id).encode('utf-8'))
                print("[MANAGER] Subscribed to", self.target_client_id)
                self.display_loop(sock)
            except Exception as e:
                print("[MANAGER] Error:", e, "-> reconnect in 5s")
                try:
                    sock.close()
                except:
                    pass
                import time
                time.sleep(5)

    def display_loop(self, sock):
        while True:
            # Receive TPKT header
            hdr = recv_all(sock, 4)
            ver, reserved, length = struct.unpack(TPKT_HEADER_FMT, hdr)
            if ver != 0x03:
                print("[MANAGER] Bad TPKT version")
                break
            payload_len = length - 4
            payload = recv_all(sock, payload_len)

            # Parse frame header (12 bytes)
            if len(payload) < 12:
                continue
            w, h, img_size = struct.unpack(">III", payload[:12])
            jpg_bytes = payload[12:]
            if len(jpg_bytes) != img_size:
                print("[MANAGER] Warning: mismatched img_size {} != {}".format(img_size, len(jpg_bytes)))

            # Decode JPEG
            np_arr = np.frombuffer(jpg_bytes, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            if frame is None:
                print("[MANAGER] Failed to decode frame")
                continue

            # Hiển thị
            cv2.imshow("Remote Screen - {}".format(self.target_client_id), frame)
            key = cv2.waitKey(1)
            if key == 27:  # ESC để thoát
                print("[MANAGER] Exiting display.")
                break
        sock.close()
        cv2.destroyAllWindows()
