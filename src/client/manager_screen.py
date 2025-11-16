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
SHARE_CTRL_HDR_FMT = ">IQBB"  # seq (I), timestamp_ms (Q), pdu_type (B), flags (B)
FRAME_FULL_HDR_FMT = ">III"   # width, height, jpeg_len

# PDU types (should match client)
PDU_TYPE_FULL = 1
PDU_TYPE_RECT = 2
PDU_TYPE_CONTROL = 3

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
        self.frame_queue = Queue(maxsize=2)
        self.stop_event = threading.Event()

    def recv_loop(self):
        while not self.stop_event.is_set():
            try:
                sock = socket.create_connection((self.server_host, self.server_port), timeout=10)
                # handshake text
                sock.sendall(b"MANAGER")
                time.sleep(0.05)
                sock.sendall(("SUBSCRIBE:" + self.target_client_id).encode('utf-8'))
                print("[MANAGER] Subscribed to client:", self.target_client_id)

                while not self.stop_event.is_set():
                    tpkt_hdr = recv_all(sock, 4)
                    ver, rsv, length = struct.unpack(TPKT_HEADER_FMT, tpkt_hdr)
                    payload_len = length - 4
                    payload = recv_all(sock, payload_len) if payload_len > 0 else b''

                    # Put payload into queue for display (payload contains Share PDU bytes)
                    if self.frame_queue.full():
                        try: self.frame_queue.get_nowait()
                        except: pass
                    self.frame_queue.put(payload)
            except Exception as e:
                print("[MANAGER] Error (reconnect in 5s):", e)
                try:
                    sock.close()
                except:
                    pass
                time.sleep(5)

    def display_loop(self):
        cv2.namedWindow(f"Remote - {self.target_client_id}", cv2.WINDOW_NORMAL)
        while not self.stop_event.is_set():
            try:
                payload = self.frame_queue.get(timeout=1)
                # parse share control header
                if len(payload) < struct.calcsize(SHARE_CTRL_HDR_FMT):
                    continue
                share_hdr = payload[:struct.calcsize(SHARE_CTRL_HDR_FMT)]
                seq, ts_ms, pdu_type, flags = struct.unpack(SHARE_CTRL_HDR_FMT, share_hdr)
                body = payload[struct.calcsize(SHARE_CTRL_HDR_FMT):]

                if pdu_type == PDU_TYPE_FULL:
                    if len(body) < struct.calcsize(FRAME_FULL_HDR_FMT):
                        continue
                    w, h, jpg_len = struct.unpack(FRAME_FULL_HDR_FMT, body[:struct.calcsize(FRAME_FULL_HDR_FMT)])
                    jpg_bytes = body[struct.calcsize(FRAME_FULL_HDR_FMT):]
                    # decode
                    np_arr = np.frombuffer(jpg_bytes, np.uint8)
                    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                    if frame is not None:
                        cv2.imshow(f"Remote - {self.target_client_id}", frame)
                        key = cv2.waitKey(1)
                        if key == 27:
                            self.stop_event.set()
                            break
                elif pdu_type == PDU_TYPE_RECT:
                    # rect header: x,y,w,h,jpeg_len (5 ints) + full_dim (2 ints) + jpg
                    if len(body) < (5*4 + 2*4):
                        continue
                    rect_hdr = struct.unpack(">IIIII", body[:20])  # x,y,w,h,jpeg_len
                    x, y, rw, rh, jpg_len = rect_hdr
                    full_dim = struct.unpack(">II", body[20:28])
                    full_w, full_h = full_dim
                    jpg_bytes = body[28:]
                    np_arr = np.frombuffer(jpg_bytes, np.uint8)
                    rect_img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                    if rect_img is None:
                        continue
                    # maintain a canvas for full image
                    if not hasattr(self, "_canvas") or self._canvas is None:
                        self._canvas = np.zeros((full_h, full_w, 3), dtype=np.uint8)
                    # place rect
                    y1, y2 = y, y + rh
                    x1, x2 = x, x + rw
                    # convert rect_img shape if needed
                    try:
                        self._canvas[y1:y2, x1:x2] = rect_img
                        cv2.imshow(f"Remote - {self.target_client_id}", self._canvas)
                        key = cv2.waitKey(1)
                        if key == 27:
                            self.stop_event.set()
                            break
                    except Exception as e:
                        # shape mismatch -> ignore
                        print("[MANAGER] Place rect error:", e)
                        continue
                else:
                    # control or unknown PDU - ignore or log
                    # you could parse control messages here (channel id, etc)
                    pass

            except Exception:
                pass
        try:
            cv2.destroyAllWindows()
        except:
            pass

    def run(self):
        t = threading.Thread(target=self.recv_loop, daemon=True)
        t.start()
        self.display_loop()
