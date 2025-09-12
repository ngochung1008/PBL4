# server.py
# Chạy trên máy server: lắng nghe kết nối, in ra mọi message client gửi

import socket
import threading

HOST = "10.10.30.128"  # lắng nghe mọi interface
PORT = 5000

def handle_client(conn, addr):
    print(f"[+] Kết nối từ {addr}")
    try:
        with conn:
            while True:
                data = conn.recv(4096)
                if not data:
                    break
                # giả sử client gửi UTF-8 text
                text = data.decode("utf-8", errors="replace")
                # in ra console server, kèm thông tin client
                for line in text.splitlines():
                    print(f"[{addr}] {line}")
    except Exception as e:
        print(f"[!] Lỗi với {addr}: {e}")
    finally:
        print(f"[-] Ngắt kết nối {addr}")

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen()
        print(f"[*] Server đang lắng nghe trên {HOST}:{PORT}")
        try:
            while True:
                conn, addr = s.accept()
                t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
                t.start()
        except KeyboardInterrupt:
            print("\n[!] Server dừng bằng Ctrl+C")

if __name__ == "__main__":
    main()
