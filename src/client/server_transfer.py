# server_transfer.py

import threading
import json
import struct
import socket # Cần import để dùng socket.error, socket.SHUT_RDWR

# Biến dùng chung cho tất cả các luồng ServerTransferHandler
transfer_conns = {} # {IP_Address: socket_object}
transfer_lock = threading.Lock()

class ServerTransferHandler:
    def __init__(self, conn, addr):
        self.conn = conn
        self.addr = addr
        self.ip = addr[0]
        # Trạng thái để theo dõi file đang được truyền (sử dụng Base64/JSON chunks)
        self.file_transfer_state = {
            "is_active": False,
            "target_ip": None,
            "file_size": 0,
            "bytes_processed": 0,
        }
        
    def run(self):
        print(f"[SERVER-TRANSFER] Connection established from: {self.ip}")
        
        # Thêm kết nối vào danh sách theo IP
        with transfer_lock:
            transfer_conns[self.ip] = self.conn
            
        try:
            buffer = b""
            while True:
                # 1. Nhận dữ liệu
                data = self.conn.recv(4096)
                if not data:
                    break
                
                buffer += data
                
                # 2. Phân tách theo giao thức: Kích thước gói (4 bytes) + Gói JSON
                while len(buffer) >= 4:
                    # Đọc kích thước gói (4 bytes đầu tiên)
                    package_size_bytes = buffer[:4]
                    if len(package_size_bytes) < 4:
                         break # Chưa đủ 4 bytes
                         
                    package_size = struct.unpack('!I', package_size_bytes)[0]
                    
                    # Kiểm tra xem đã nhận đủ gói chưa
                    if len(buffer) >= 4 + package_size:
                        package_data = buffer[4:4 + package_size]
                        buffer = buffer[4 + package_size:]
                        
                        self.handle_package(package_data)
                    else:
                        break # Chờ thêm dữ liệu
                        
        except Exception as e:
            # Gỡ bỏ kết nối nếu có lỗi
            print(f"[SERVER-TRANSFER] Error for {self.ip}: {e}")
            
        finally:
            print(f"[SERVER-TRANSFER] Disconnected: {self.ip}")
            with transfer_lock:
                if self.ip in transfer_conns and transfer_conns[self.ip] == self.conn:
                    del transfer_conns[self.ip]
            self.conn.close()

    def handle_package(self, package_data):
        try:
            # Gói JSON chứa metadata
            package_str = package_data.decode('utf-8')
            pkg = json.loads(package_str)
            
            target_ip = pkg.get("target_ip")
            pkg["sender"] = self.ip # Đảm bảo IP người gửi là chính xác
            
            pkg_type = pkg.get("type")
            
            # --- Cập nhật trạng thái truyền file (Chỉ theo dõi tiến trình) ---
            if pkg_type == "file_meta":
                # Kích hoạt trạng thái truyền file (dùng để theo dõi tiến trình trên server)
                self.file_transfer_state["is_active"] = True
                self.file_transfer_state["target_ip"] = target_ip
                file_size = pkg["data"].get("size", 0)
                self.file_transfer_state["file_size"] = file_size
                self.file_transfer_state["bytes_processed"] = 0
                print(f"[SERVER-TRANSFER] File meta received. Size: {file_size}. Relaying meta...")
            elif pkg_type == "file_data":
                # Cập nhật số byte đã xử lý
                # Sử dụng độ dài của chuỗi Base64 (ước tính)
                estimated_bytes = len(pkg["data"].get("chunk", ""))
                self.file_transfer_state["bytes_processed"] += estimated_bytes
                
                if self.file_transfer_state["file_size"] > 0:
                     progress = (self.file_transfer_state["bytes_processed"] / self.file_transfer_state["file_size"]) * 100
                     # print(f"[SERVER-TRANSFER] Relaying file data. Progress: {progress:.2f}%")
                     pass # Chỉ in ra khi cần debug
                
            elif pkg_type == "file_end":
                print(f"[SERVER-TRANSFER] File transfer complete ({self.file_transfer_state['file_size']} bytes).")
                self.file_transfer_state["is_active"] = False
                self.file_transfer_state["target_ip"] = None
                self.file_transfer_state["file_size"] = 0
                self.file_transfer_state["bytes_processed"] = 0
            
            # --- Relay gói JSON có điều kiện ---
            if target_ip and target_ip in transfer_conns:
                target_conn = transfer_conns[target_ip]
                # Gói dữ liệu gốc cần được đóng gói lại (Kích thước + Dữ liệu)
                full_package_to_send = struct.pack('!I', len(package_str)) + package_data
                
                try:
                    target_conn.sendall(full_package_to_send)
                except Exception as e:
                    print(f"[SERVER-TRANSFER] Failed to relay to {target_ip}: {e}")
                    # Xử lý ngắt kết nối đích
                    with transfer_lock:
                        if target_ip in transfer_conns: del transfer_conns[target_ip]
            elif target_ip is None or target_ip == 'all':
                 # Tùy chọn: Gửi cho tất cả Manager/Client
                 # Cần code loop qua transfer_conns và gửi cho từng người
                 pass 
            else:
                 # print(f"[SERVER-TRANSFER] Target IP {target_ip} not found.")
                 pass

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