# manager_screen.py
# -*- coding: utf-8 -*-
from __future__ import print_function
import socket
import struct
import os
import time

TPKT_HEADER_FMT = ">BBH"  # version(1), reserved(1), length(2)

class ManagerScreenReceiver(object):
    """
    Manager subscribes to a client_id on the server and receives forwarded frames.
    It saves received frames into out_dir/<client_id>/frame_xxx.jpg
    """
    def __init__(self, server_host, server_port, client_id, out_dir="manager_frames"):
        self.server_host = server_host
        self.server_port = server_port
        self.client_id = client_id
        self.out_dir = out_dir
        self.frame_count = 0
        try:
            os.makedirs(os.path.join(out_dir, client_id))
        except:
            pass

    def recv_all(self, sock, n):
        data = b''
        while len(data) < n:
            chunk = sock.recv(n - len(data))
            if not chunk:
                raise ConnectionError("Socket closed while reading")
            data += chunk
        return data

    def run(self):
        while True:
            try:
                print("[MANAGER] Connecting to {}:{} ...".format(self.server_host, self.server_port))
                sock = socket.create_connection((self.server_host, self.server_port), timeout=10)
                # send handshake MANAGER + subscribe
                try:
                    sock.sendall(b"MANAGER")
                    time.sleep(0.05)
                    sock.sendall(("SUBSCRIBE:" + self.client_id).encode('utf-8'))
                except:
                    sock.sendall("MANAGER")
                    time.sleep(0.05)
                    sock.sendall("SUBSCRIBE:" + self.client_id)
                print("[MANAGER] Subscribed to client:", self.client_id)

                while True:
                    # read TPKT header
                    hdr = self.recv_all(sock, 4)
                    ver, reserved, length = struct.unpack(TPKT_HEADER_FMT, hdr)
                    if ver != 0x03:
                        print("[MANAGER] Unexpected TPKT version:", ver)
                        break
                    payload_len = length - 4
                    payload = self.recv_all(sock, payload_len)
                    if len(payload) < 12:
                        print("[MANAGER] payload too small")
                        continue
                    w, h, img_size = struct.unpack(">III", payload[:12])
                    remaining = payload[12:]
                    if len(remaining) < img_size:
                        remaining += self.recv_all(sock, img_size - len(remaining))
                    jpg = remaining[:img_size]
                    self.frame_count += 1
                    filename = os.path.join(self.out_dir, self.client_id, "frame_{:06d}.jpg".format(self.frame_count))
                    with open(filename, "wb") as f:
                        f.write(jpg)
                    print("[MANAGER] Saved", filename, "({}x{}, {} bytes)".format(w, h, len(jpg)))
            except KeyboardInterrupt:
                print("\n[MANAGER] Exiting by user.")
                try:
                    sock.close()
                except:
                    pass
                break
            except Exception as e:
                print("[MANAGER] Error:", e, "-> reconnect in 5s")
                try:
                    sock.close()
                except:
                    pass
                time.sleep(5)
