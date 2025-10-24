# client_transfer.py

import sys
import socket
import struct
import json
import threading
import os
import time

class ClientTransfer:
    """
    Lớp ClientTransfer:
    - Kết nối đến server_transfer.py (ở SERVER)
    - Nhận JSON gói tin ("chat", "file_meta", "file_data")
    - Nhận file binary và lưu xuống thư mục ./received_files/
    """
    def __init__(self, server_host, transfer_port, username="client"):
        self.server_host = server_host
        self.transfer_port = transfer_port
        self.username = username
        self.sock = None
        self.is_running = True
        self.save_dir = os.path.join(os.getcwd(), "received_files")

        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)

    def connect(self):
        """Kết nối tới server transfer"""
        try:
            self.sock = socket.create_connection((self.server_host, self.transfer_port), timeout=10)
            print(f"[CLIENT TRANSFER] Connected to {self.server_host}:{self.transfer_port}")
            return True
        except Exception as e:
            print(f"[CLIENT TRANSFER] Connection failed: {e}")
            return False

    def start(self):
        """Bắt đầu luồng nhận dữ liệu từ server"""
        if not self.sock:
            if not self.connect():
                return
        threading.Thread(target=self._recv_loop, daemon=True).start()

    def _recv_loop(self):
        """Vòng lặp chính nhận gói tin"""
        buffer = b""
        try:
            while self.is_running:
                # Nhận header độ dài (4 bytes)
                header = self._recv_exact(4)
                if not header:
                    break
                pkg_len = struct.unpack("!I", header)[0]

                # Nhận nội dung JSON
                pkg_data = self._recv_exact(pkg_len)
                if not pkg_data:
                    break

                try:
                    pkg = json.loads(pkg_data.decode("utf-8"))
                except Exception as e:
                    print("[CLIENT TRANSFER] JSON parse error:", e)
                    continue

                pkg_type = pkg.get("type")
                sender = pkg.get("sender")
                data = pkg.get("data")

                # === Xử lý các loại gói ===
                if pkg_type == "chat":
                    print(f"[CHAT] {sender}: {data}")

                elif pkg_type == "file_meta":
                    filename = data.get("filename", "unknown_file")
                    filesize = data.get("filesize", 0)
                    print(f"[CLIENT TRANSFER] Receiving file '{filename}' ({filesize} bytes) from {sender} ...")

                    self._recv_file(filename, filesize)

                else:
                    print(f"[CLIENT TRANSFER] Unknown package type: {pkg_type}")

        except Exception as e:
            print(f"[CLIENT TRANSFER] Error in receive loop: {e}")
        finally:
            if self.sock:
                self.sock.close()
            print("[CLIENT TRANSFER] Disconnected from transfer server.")

    def _recv_file(self, filename, filesize):
        """Nhận dữ liệu file binary sau khi có metadata"""
        file_path = os.path.join(self.save_dir, filename)
        received = 0

        try:
            with open(file_path, "wb") as f:
                while received < filesize:
                    chunk = self.sock.recv(min(4096, filesize - received))
                    if not chunk:
                        break
                    f.write(chunk)
                    received += len(chunk)
                    self._print_progress(received, filesize)

            print(f"\n[CLIENT TRANSFER] File saved: {file_path}")
        except Exception as e:
            print(f"[CLIENT TRANSFER] Error receiving file: {e}")

    def _print_progress(self, done, total):
        """Hiển thị tiến trình nhận file"""
        percent = done * 100 / total if total > 0 else 0
        sys.stdout.write(f"\r   → {percent:.1f}% ({done}/{total} bytes)")
        sys.stdout.flush()

    def _recv_exact(self, size):
        """Nhận đúng size byte (dừng nếu socket đóng)"""
        buf = b""
        while len(buf) < size:
            chunk = self.sock.recv(size - len(buf))
            if not chunk:
                return None
            buf += chunk
        return buf
