#!/usr/bin/env python3
import socket
import threading
import sys
import argparse

def recv_messages(sock):
    try:
        while True:
            data = sock.recv(4096)
            if not data:
                print("[INFO] Mất kết nối tới server.")
                break
            print(f"\rSERVER: {data.decode('utf-8', errors='replace').rstrip()}\n> ", end="")
    except Exception as e:
        print(f"\n[ERROR] Lỗi nhận: {e}")

def send_messages(sock):
    try:
        while True:
            msg = input("> ")
            if msg.strip().lower() == "/quit":
                try:
                    sock.shutdown(socket.SHUT_RDWR)
                except Exception:
                    pass
                sock.close()
                print("[INFO] Đã thoát.")
                break
            sock.sendall((msg + "\n").encode("utf-8"))
    except (EOFError, KeyboardInterrupt):
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass
        sock.close()
        print("\n[INFO] Đã thoát.")

def main():
    parser = argparse.ArgumentParser(description="Simple LAN Chat - Client")
    parser.add_argument("--server-ip", required=True, help="IP máy chạy server (ví dụ 192.168.1.10)")
    parser.add_argument("--port", type=int, default=5000, help="Cổng TCP (mặc định 5000)")
    args = parser.parse_args()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        print(f"[CLIENT] Kết nối tới {args.server_ip}:{args.port} ...")
        sock.connect((args.server_ip, args.port))
        print("[CLIENT] Đã kết nối! Gõ tin nhắn và Enter để gửi. Gõ /quit để thoát.")

        t_recv = threading.Thread(target=recv_messages, args=(sock,), daemon=True)
        t_recv.start()

        send_messages(sock)

if __name__ == "__main__":
    main()
