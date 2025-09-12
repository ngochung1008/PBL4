# client.py
# Chạy trên máy client: nhập dòng text, gửi lên server
# Lưu ý: client chỉ gửi những gì bạn chủ động nhập dòng (input)

import socket
import sys

SERVER_HOST = "10.10.30.128"  # thay bằng IP server, ví dụ "192.168.1.10"
SERVER_PORT = 5000

def main():
    if len(sys.argv) >= 2:
        SERVER_HOST = sys.argv[1]
    else:
        SERVER_HOST = SERVER_HOST  # dùng giá trị mặc định trong file

    print(f"[*] Kết nối tới {SERVER_HOST}:{SERVER_PORT} ...")
    try:
        with socket.create_connection((SERVER_HOST, SERVER_PORT)) as s:
            print("[*] Đã kết nối. Gõ dòng rồi Enter để gửi. Gõ /quit để thoát.")
            while True:
                try:
                    line = input("> ")
                except EOFError:
                    break
                if not line:
                    continue
                if line.strip() == "/quit":
                    print("[*] Đóng kết nối.")
                    break
                # gửi line kèm newline
                s.sendall((line + "\n").encode("utf-8"))
    except Exception as e:
        print(f"[!] Lỗi kết nối: {e}")

if __name__ == "__main__":
    main()
