# server_view_live.py
import socket
import struct
import io
import cv2
import numpy as np
from PIL import Image

HOST = "0.0.0.0"
PORT = 5000

def recvall(sock, n):
    data = bytearray()
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            return None
        data.extend(packet)
    return data

def handle_client(conn, addr):
    print("Connected by", addr)
    try:
        while True:
            header = recvall(conn, 4)
            if not header:
                print("Client disconnected")
                break
            (length,) = struct.unpack(">I", header)
            payload = recvall(conn, length)
            if not payload:
                print("Client disconnected during payload")
                break

            # Hiển thị ảnh từ bytes
            img = Image.open(io.BytesIO(payload))
            cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            cv2.imshow(f"Client {addr[0]}", cv_img)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        conn.close()
        cv2.destroyAllWindows()

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen(5)
        print(f"Server listening on {HOST}:{PORT}")
        while True:
            conn, addr = s.accept()
            handle_client(conn, addr)

if __name__ == "__main__":
    main()