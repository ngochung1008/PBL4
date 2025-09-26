import socket
import threading
import struct
import io
import cv2
import numpy as np
from PIL import Image

CONTROL_PORT = 9010   # manager <-> client B (chuyển lệnh)
SCREEN_PORT = 5000    # client B -> server (stream màn hình)

clients = {}  # lưu client B {addr: conn}

# ========================
# SERVER CONTROL
# ========================
def handle_manager(conn, addr):
    print("[SERVER] Manager connected:", addr)
    try:
        while True:
            cmd = conn.recv(1024).decode("utf-8")
            if not cmd:
                break
            print(f"[Manager] {cmd}")
            # gửi lệnh cho tất cả client B
            for caddr, cconn in list(clients.items()):
                try:
                    cconn.sendall(cmd.encode("utf-8"))
                    print(f"Sent to client {caddr}")
                except:
                    pass
    finally:
        conn.close()

def handle_client(conn, addr):
    print("[SERVER] Client B connected:", addr)
    clients[addr] = conn
    try:
        while True:
            data = conn.recv(1024)
            if not data:
                break
            print(f"[Client B {addr}] {data.decode('utf-8')}")
    finally:
        del clients[addr]
        conn.close()

def start_control_server():
    # socket manager
    sm = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sm.bind(("0.0.0.0", CONTROL_PORT))
    sm.listen(1)
    print(f"[SERVER] Listening for manager on port {CONTROL_PORT}")

    # socket client B
    sc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sc.bind(("0.0.0.0", CONTROL_PORT+1))
    sc.listen(5)
    print(f"[SERVER] Listening for clients on port {CONTROL_PORT+1}")

    def accept_loop(sock, handler):
        while True:
            conn, addr = sock.accept()
            threading.Thread(target=handler, args=(conn, addr), daemon=True).start()

    threading.Thread(target=accept_loop, args=(sm, handle_manager), daemon=True).start()
    threading.Thread(target=accept_loop, args=(sc, handle_client), daemon=True).start()

# ========================
# SERVER VIEW SCREEN
# ========================
def recvall(sock, n):
    data = bytearray()
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            return None
        data.extend(packet)
    return data

def start_screen_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("0.0.0.0", SCREEN_PORT))
        s.listen(5)
        print(f"[SERVER] Screen server listening on {SCREEN_PORT}")
        while True:
            conn, addr = s.accept()
            print("Screen stream from", addr)
            try:
                while True:
                    header = recvall(conn, 4)
                    if not header:
                        break
                    (length,) = struct.unpack(">I", header)
                    payload = recvall(conn, length)
                    if not payload:
                        break

                    img = Image.open(io.BytesIO(payload))
                    cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                    cv2.imshow(f"Client {addr[0]}", cv_img)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break
            finally:
                conn.close()
                cv2.destroyAllWindows()

# ========================
# MAIN
# ========================
if __name__ == "__main__":
    threading.Thread(target=start_control_server, daemon=True).start()
    start_screen_server()