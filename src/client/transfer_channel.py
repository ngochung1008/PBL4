# transfer_channel.py

import socket
import threading
import json
import struct
import os 

class TransferChannel:
    def __init__(self, server_host, transfer_port, on_receive_callback):
        self.server_host = server_host
        self.transfer_port = transfer_port
        self.on_receive = on_receive_callback
        self.sock = None
        self.is_connected = False
        self.buffer = b""

    def connect(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.server_host, self.transfer_port))
            self.is_connected = True
            print("[TRANSFER] Connected to server for chat/file transfer.")
            threading.Thread(target=self._recv_loop, daemon=True).start()
            return True
        except Exception as e:
            print(f"[TRANSFER] Connection error: {e}")
            return False

    def _recv_loop(self):
        try:
            while self.is_connected:
                data = self.sock.recv(4096)
                if not data:
                    break
                
                self.buffer += data
                
                # Logic phân tách gói tin
                while len(self.buffer) >= 4:
                    package_size = struct.unpack('!I', self.buffer[:4])[0]
                    
                    if len(self.buffer) >= 4 + package_size:
                        package_data = self.buffer[4:4 + package_size]
                        self.buffer = self.buffer[4 + package_size:]
                        
                        try:
                            pkg = json.loads(package_data.decode('utf-8'))
                            self.on_receive(pkg)
                        except json.JSONDecodeError:
                            print("[TRANSFER] Received invalid package format.")
                        
                    else:
                        break # Chưa nhận đủ gói
        except Exception as e:
            print(f"[TRANSFER] Receiver loop error: {e}")
            
        finally:
            self.is_connected = False
            self.close()

    def close(self):
        self.is_connected = False
        if self.sock:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
                self.sock.close()
            except Exception:
                pass
            self.sock = None

    # Hàm gửi dữ liệu (Chat hoặc File Meta)
    def send_package(self, pkg_type, target_ip, data):
        if not self.is_connected:
            print("[TRANSFER] Not connected to server.")
            return

        pkg = {
            "type": pkg_type,
            "target_ip": target_ip,
            "data": data,
        }
        
        try:
            # Đóng gói JSON
            pkg_str = json.dumps(pkg)
            pkg_bytes = pkg_str.encode('utf-8')
            pkg_size = len(pkg_bytes)
            
            # Gửi: Kích thước gói (4 bytes) + Dữ liệu gói
            header = struct.pack('!I', pkg_size)
            self.sock.sendall(header + pkg_bytes)
            return True
        except Exception as e:
            print(f"[TRANSFER] Send error: {e}")
            self.is_connected = False
            return False
        
    def send_file(self, file_path, target_ip):
        """Gửi file: Gửi metadata (JSON) trước, sau đó gửi dữ liệu thô (binary)."""
        if not self.is_connected:
            print("[TRANSFER] Not connected to server.")
            return False

        try:
            file_size = os.path.getsize(file_path)
            file_name = os.path.basename(file_path)
        except OSError as e:
            print(f"[TRANSFER] Error accessing file: {e}")
            return False

        # 1. Gửi gói Metadata
        file_meta_data = {
            "filename": file_name,
            "size": file_size,
        }
        
        if not self.send_package("file_meta", target_ip, file_meta_data):
            print("[TRANSFER] Failed to send file metadata.")
            return False

        print(f"[TRANSFER] Sent metadata for {file_name} to {target_ip}. Starting data transfer...")
        
        # 2. Gửi dữ liệu file thô ngay sau gói metadata
        self._send_file_data(file_path)
        return True

    def _send_file_data(self, file_path):
        """Gửi dữ liệu file thô qua socket hiện tại (Không dùng JSON/Header nữa)."""
        try:
            with open(file_path, 'rb') as f:
                while True:
                    bytes_read = f.read(4096)
                    if not bytes_read:
                        break
                    # Gửi data thô
                    self.sock.sendall(bytes_read)
            print(f"[TRANSFER] Finished sending file data for {os.path.basename(file_path)}.")
        except Exception as e:
            print(f"[TRANSFER] Error sending file data: {e}")
            self.is_connected = False
            self.close()