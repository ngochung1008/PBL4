#!/usr/bin/env python3
import socket
import threading
import sys
import argparse

def recv_messages(conn, addr):
    try:
        with conn:
            while True:
                data = conn.recv(4096)
                if not data:
                    print("[INFO] Người kia đã thoát.")
                    break
                print(f"\r{addr[0]}: {data.decode('utf-8', errors='replace').rstrip()}\n> ", end="")
    except Exception as e:
        print(f"\n[ERROR] Lỗi nhận: {e}")

def send_messages(conn):
    try:
        while True:
            msg = input("> ")
            if msg.strip().lower() == "/quit":
                try:
                    conn.shutdown(socket.SHUT_RDWR)
                except Exception:
                    pass
                conn.close()
                print("[INFO] Đã thoát.")
                break
            conn.sendall((msg + "\n").encode("utf-8"))
    except (EOFError, KeyboardInterrupt):
        try:
            conn.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass
        conn.close()
        print("\n[INFO] Đã thoát.")

def main():
    parser = argparse.ArgumentParser(description="Simple LAN Chat - Server")
    parser.add_argument("--host", default="0.0.0.0", help="Địa chỉ lắng nghe (mặc định 0.0.0.0)")
    parser.add_argument("--port", type=int, default=5000, help="Cổng TCP (mặc định 5000)")
    args = parser.parse_args()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((args.host, args.port))
        s.listen(1)
        print(f"[SERVER] Đang lắng nghe tại {args.host}:{args.port} ...")
        print("[HƯỚNG DẪN] Khi kết nối xong, gõ tin nhắn và Enter để gửi. Gõ /quit để thoát.")
        conn, addr = s.accept()
        print(f"[SERVER] Đã kết nối từ {addr[0]}:{addr[1]}")

        t_recv = threading.Thread(target=recv_messages, args=(conn, addr), daemon=True)
        t_recv.start()

        send_messages(conn)

if __name__ == "__main__":
    main()