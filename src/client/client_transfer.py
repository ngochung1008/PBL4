# client_transfer.py

import sys
import socket
import struct
import json
import threading
import os
import time
import base64

class ClientTransfer:
    """
    Lớp ClientTransfer:
    - Kết nối đến server_transfer.py (ở SERVER)
    - Nhận JSON gói tin ("chat", "file_meta", "file_data")
    - Nhận file Base64 chunk, giải mã và lưu
    """
    def __init__(self, server_host, transfer_port, username="client"):
        self.server_host = server_host
        self.transfer_port = transfer_port
        self.username = username
        self.sock = None
        self.is_running = True
        self.save_dir = os.path.join(os.getcwd(), "received_files")
        
        # Biến theo dõi quá trình nhận file
        self.receiving_file_name = None 
        self.receiving_file_path = None 
        self.receiving_file_handle = None 
        self.received_bytes = 0
        self.target_filesize = 0

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

    def _handle_package(self, pkg):
        pkg_type = pkg.get("type")
        sender = pkg.get("sender")
        data = pkg.get("data")
        
        if pkg_type == "chat":
            print(f"[CHAT] {sender}: {data}")

        elif pkg_type == "file_meta":
            filename = data.get("filename", "unknown_file")
            filesize = data.get("size", 0) 
            
            if self.receiving_file_handle:
                 self.receiving_file_handle.close()
                 print(f"\n[CLIENT TRANSFER] WARNING: Closed previous file ({self.receiving_file_name}) before completion.")
            
            self.receiving_file_name = filename
            self.receiving_file_path = os.path.join(self.save_dir, filename)
            
            try:
                self.receiving_file_handle = open(self.receiving_file_path, "wb")
            except Exception as e:
                print(f"[CLIENT TRANSFER] Failed to open file {filename}: {e}")
                self.receiving_file_handle = None
                return

            self.received_bytes = 0
            self.target_filesize = filesize

            print(f"[CLIENT TRANSFER] Receiving file '{filename}' ({filesize} bytes) from {sender} ...")

        elif pkg_type == "file_data":
            chunk_b64 = data.get("chunk", "")
            bytes_len = data.get("bytes", 0)
            
            if self.receiving_file_handle:
                try:
                    chunk = base64.b64decode(chunk_b64)
                    self.receiving_file_handle.write(chunk)
                    self.received_bytes += bytes_len
                    self._print_progress(self.received_bytes, self.target_filesize)
                except Exception as e:
                    print(f"\n[CLIENT TRANSFER] Error writing chunk: {e}")

        elif pkg_type == "file_end":
            if self.receiving_file_handle:
                self.receiving_file_handle.close()
                self.receiving_file_handle = None
                print(f"\n[CLIENT TRANSFER] File saved: {self.receiving_file_path}")
            else:
                print("\n[CLIENT TRANSFER] Received file_end without active transfer.")

        else:
            if pkg_type not in ["file_meta", "file_data", "file_end"]:
                 print(f"[CLIENT TRANSFER] Unknown package type: {pkg_type}")

    def _recv_loop(self):
        """Vòng lặp chính nhận gói tin"""
        try:
            while self.is_running:
                header = self._recv_exact(4)
                if not header:
                    break
                pkg_len = struct.unpack("!I", header)[0]

                pkg_data = self._recv_exact(pkg_len)
                if not pkg_data:
                    break

                try:
                    pkg = json.loads(pkg_data.decode("utf-8"))
                    self._handle_package(pkg) 
                except Exception as e:
                    print("[CLIENT TRANSFER] JSON parse error:", e)
                    continue

        except Exception as e:
            print(f"[CLIENT TRANSFER] Error in receive loop: {e}")
        finally:
            if self.receiving_file_handle:
                try:
                    self.receiving_file_handle.close()
                    print(f"[CLIENT TRANSFER] WARNING: File {self.receiving_file_name} was incomplete, but closed due to disconnect.")
                except Exception:
                    pass
            if self.sock:
                self.sock.close()
            print("[CLIENT TRANSFER] Disconnected from transfer server.")

    def _print_progress(self, done, total):
        """Hiển thị tiến trình nhận file"""
        percent = done * 100 / total if total > 0 else 0
        sys.stdout.write(f"\r   → {percent:.1f}% ({done}/{total} bytes)")
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