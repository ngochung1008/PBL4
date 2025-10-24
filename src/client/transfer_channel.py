# transfer_channel.py

import sys
import socket
import threading
import json
import struct
import os 
import base64
import time 

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
                
                while len(self.buffer) >= 4:
                    if len(self.buffer) < 4: break 
                        
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
                        break 
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

    def send_package(self, pkg_type, target_ip, data):
        if not self.is_connected:
            return False

        pkg = {
            "type": pkg_type,
            "target_ip": target_ip,
            "data": data,
        }
        
        try:
            pkg_str = json.dumps(pkg)
            pkg_bytes = pkg_str.encode('utf-8')
            pkg_size = len(pkg_bytes)
            
            header = struct.pack('!I', pkg_size)
            self.sock.sendall(header + pkg_bytes)
            return True
        except Exception as e:
            self.is_connected = False
            self.close()
            return False
        
    def send_file(self, file_path, target_ip):
        """Gửi file: Gửi metadata, sau đó gửi dữ liệu theo CHUNKS JSON/Base64."""
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

        print(f"[TRANSFER] Sent metadata for {file_name} to {target_ip}. Starting CHUNK data transfer...")
        
        # 2. Gửi dữ liệu file theo CHUNKS
        CHUNK_SIZE = 3072
        bytes_sent = 0
        
        try:
            with open(file_path, 'rb') as f:
                while True:
                    chunk = f.read(CHUNK_SIZE)
                    if not chunk: break
                        
                    base64_chunk = base64.b64encode(chunk).decode('utf-8')
                    
                    file_data_pkg = {
                        "chunk": base64_chunk,
                        "bytes": len(chunk)
                    }
                    if not self.send_package("file_data", target_ip, file_data_pkg):
                        raise Exception("Failed to send file data chunk.")
                        
                    bytes_sent += len(chunk)
                    sys.stdout.write(f"\r[TRANSFER] Progress: {bytes_sent/file_size*100:.1f}%")
                    sys.stdout.flush()
                    time.sleep(0.001) 
            
            # 3. Gửi gói kết thúc
            self.send_package("file_end", target_ip, {})
            print(f"\n[TRANSFER] Finished sending file data for {file_name}.")
            return True
            
        except Exception as e:
            print(f"\n[TRANSFER] Error sending file data: {e}")
            self.is_connected = False
            self.close()
            return False