# server.py

import socket
import threading
import struct
import io
import cv2
import numpy as np
from PIL import Image
import threading
from server_screen import ServerScreen   # import module screen

CONTROL_PORT = 9010   # Manager -> Server
CLIENT_PORT = 9011    # Server -> Client
SCREEN_PORT = 5000    # Client - Server (stream màn hình)
clients = []  # list kết nối client (chỉ 1 hoặc nhiều)

# ========================
# SERVER CONTROL
# ========================
def handle_manager(conn, addr):
    print("[SERVER] Manager connected:", addr)
    try:
        while True:
            data = conn.recv(4096)
            if not data:
                break
            # forward cho tất cả client
            for c in list(clients):
                try:
                    c.sendall(data)
                except:
                    clients.remove(c)
    finally:
        conn.close()

def handle_client(conn, addr):
    print("[SERVER] Client connected:", addr)
    clients.append(conn)
    try:
        while True:
            data = conn.recv(1024)
            if not data:
                break
    finally:
        clients.remove(conn)
        conn.close()

def start_control_server():
    # Manager input
    sm = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sm.bind(("0.0.0.0", CONTROL_PORT))
    sm.listen(1)
    print(f"[SERVER] Listening for manager on port {CONTROL_PORT}")

    # Client input
    sc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sc.bind(("0.0.0.0", CLIENT_PORT))
    sc.listen(5)
    print(f"[SERVER] Listening for clients on port {CLIENT_PORT}")

    def accept_loop(sock, handler):
        while True:
            conn, addr = sock.accept()
            threading.Thread(target=handler, args=(conn, addr), daemon=True).start()

    threading.Thread(target=accept_loop, args=(sm, handle_manager), daemon=True).start()
    threading.Thread(target=accept_loop, args=(sc, handle_client), daemon=True).start()

# ========================
# MAIN
# ========================
if __name__ == "__main__":
    # chạy control server
    threading.Thread(target=start_control_server, daemon=True).start()

    # chạy screen server relay Client <-> Manager
    screen_server = ServerScreen("0.0.0.0", SCREEN_PORT)
    screen_server.run()