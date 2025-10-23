# server_screen.py

import socket
import threading
import struct
import json
import time

class ServerScreen:
    def __init__(self, host="0.0.0.0", port=5000):
        self.host = host
        self.port = port

        # { Client_IP: [socket_conn, latest_frame_data] }
        self.clients = {}  
        self.clients_lock = threading.Lock()

        # { Manager_IP: [socket_conn, desired_client_ip] }
        # desired_client_ip: IP của Client mà Manager muốn xem
        self.managers = {}
        self.managers_lock = threading.Lock()

        # Danh sách kết nối đang hoạt động
        self.active_client_ips = []

        # Luồng gửi frame định kỳ cho tất cả managers
        self.broadcast_thread = threading.Thread(target=self._periodic_broadcast_loop, daemon=True)
        self.broadcast_thread.start()

    # Hàm tiện ích để lấy danh sách Client IP đang hoạt động
    def get_active_client_ips(self):
        with self.clients_lock:
            return list(self.clients.keys())

    # def broadcast_to_managers(self, data):
    #     """Gửi ảnh tới tất cả managers"""
    #     with self.lock:
    #         for m in list(self.managers):
    #             try:
    #                 m.sendall(data)
    #             except:
    #                 print("[SERVER SCREEN] Manager disconnected")
    #                 self.managers.remove(m)

    # Logic broadcast gửi frame định kỳ (chủ động)
    def _periodic_broadcast_loop(self):
        """Gửi frame định kỳ cho Managers theo yêu cầu."""
        while True:
            time.sleep(1/30) # Tần suất kiểm tra để gửi frame (ví dụ 30 FPS)
            
            # Lặp qua tất cả Managers
            with self.managers_lock:
                managers_to_remove = []
                for manager_ip, (m_conn, desired_ip) in self.managers.items():
                    frame_data = None
                    
                    # 1. Kiểm tra xem Client mong muốn có đang stream không
                    with self.clients_lock:
                        if desired_ip in self.clients:
                            # Lấy frame mới nhất từ Client mong muốn
                            frame_data = self.clients[desired_ip][1] 
                    
                    # 2. Nếu có frame và Manager đang mong muốn
                    if frame_data:
                        try:
                            # Gửi header + payload
                            m_conn.sendall(frame_data) 
                        except:
                            managers_to_remove.append(manager_ip)
                            
                # Xóa managers bị ngắt kết nối
                for ip in managers_to_remove:
                    m_conn = self.managers[ip][0]
                    del self.managers[ip]
                    try: m_conn.close()
                    except: pass
                    print(f"[SERVER SCREEN] Manager {ip} disconnected (Broadcast failure)")
    
    def _recv_exact(self, conn, n):
        data = b""
        while len(data) < n:
            chunk = conn.recv(n - len(data))
            if not chunk:
                raise ConnectionError("Lost connection")
            data += chunk
        return data

    def handle_client(self, conn, addr):
        """Nhận dữ liệu màn hình từ Client và lưu trữ."""
        client_ip = addr[0]
        print("[SERVER SCREEN] Client stream connected:", client_ip)

        # Ghi nhận kết nối Client
        with self.clients_lock:
            # [socket_conn, latest_frame_data]
            self.clients[client_ip] = [conn, None] 
            self.active_client_ips = list(self.clients.keys()) 

        try:
            while True:
                # Nhận header 12 byte: width(4), height(4), length(4)
                header = self._recv_exact(conn, 12)
                w, h, length = struct.unpack(">III", header)
                payload = self._recv_exact(conn, length)

                # Lưu trữ frame mới nhất (header + payload)
                with self.clients_lock:
                    self.clients[client_ip][1] = header + payload

                # Gửi lại cho managers (gồm header + ảnh)
                # self.broadcast_to_managers(header + payload)
        except Exception as e:
            # print(f"[SERVER SCREEN] Client {client_ip} error: {e}")
            pass
        finally:
            conn.close()
            with self.clients_lock:
                if client_ip in self.clients:
                    del self.clients[client_ip]
                    self.active_client_ips = list(self.clients.keys())
            print(f"[SERVER SCREEN] Client {client_ip} disconnected")

    # Xử lý Manager gửi yêu cầu xem màn hình
    def handle_manager_request(self, manager_conn, manager_ip):
        """Manager gửi yêu cầu chọn Client hoặc yêu cầu danh sách Client."""
        
        # Hàm gửi lại danh sách Client (ví dụ)
        def send_client_list():
            # Sử dụng CONTROL_PORT để gửi thông tin này nếu cần UI.
            # Ở đây ta gửi qua kênh stream (không chuẩn lắm, nhưng hoạt động).
            # Tốt hơn nên dùng kênh TRANSFER_PORT để gửi metadata này.
            active_clients = self.get_active_client_ips()
            response = json.dumps({"type": "client_list", "clients": active_clients})
            # Gói lại response theo giao thức 4 bytes length + payload
            response_data = struct.pack(">I", len(response.encode())) + response.encode()
            try:
                manager_conn.sendall(response_data)
            except:
                pass

        try:
            # Manager sẽ gửi lệnh yêu cầu xem màn hình
            while True:
                # Nhận gói lệnh từ Manager (giả định dùng giao thức JSON/4-byte length)
                # Tạm thời chỉ đọc 4KB và xử lý
                data = manager_conn.recv(4096) 
                if not data: break

                # Giả định Manager gửi: {"type": "select", "ip": "192.168.1.10"}
                try:
                    # RẤT KHÔNG CHUẨN: Vì kênh stream không dùng giao thức gói JSON/length.
                    # Nhưng ta giả định Manager chỉ gửi một lệnh đơn giản, ví dụ: 'SELECT:192.168.1.10'
                    command = data.decode('utf-8').strip()
                    
                    if command.startswith("SELECT:"):
                        desired_ip = command.split(":")[1]
                        with self.managers_lock:
                            if manager_ip in self.managers:
                                self.managers[manager_ip][1] = desired_ip
                                print(f"[SERVER SCREEN] Manager {manager_ip} now watching {desired_ip}")
                    # Nếu Manager yêu cầu danh sách client
                    elif command == "GET_LIST":
                         send_client_list()
                         
                except Exception as e:
                    print(f"[SERVER SCREEN] Manager {manager_ip} command error: {e}")
                    pass
                    
        except:
            # Mất kết nối yêu cầu từ Manager
            pass
        finally:
             # Manager request channel closed, but connection might still be active in self.managers list
             pass

    def _manager_receiver_loop(self, conn, addr):
        """
        Luồng lắng nghe/giữ kết nối cho Manager. 
        Mặc dù Manager không gửi gì, nhưng cần vòng lặp để giữ conn mở
        và xử lý khi Manager đóng kết nối.
        """
        try:
            # Manager chỉ nhận dữ liệu, nhưng cần một vòng lặp để giữ luồng/xử lý ngắt
            while True:
                # Đọc một byte để kiểm tra ngắt kết nối một cách chủ động hơn
                # Tuy nhiên, cách đơn giản nhất là chỉ chờ, và socket sẽ báo lỗi khi gửi (trong broadcast)
                # Ta thêm một lần đọc nhỏ để phát hiện ngắt kết nối (Nếu Manager gửi tín hiệu đóng).
                conn.settimeout(1.0) # Đặt timeout ngắn để không bị chặn vô hạn
                try:
                    data = conn.recv(1)
                    if not data:
                        break # Manager đã đóng kết nối
                except socket.timeout:
                    # Bỏ qua timeout và tiếp tục
                    continue
                except Exception:
                    break # Lỗi khác (Ngắt kết nối)
        except Exception as e:
            # print(f"[SERVER SCREEN] Manager receive error: {e}")
            pass
        finally:
            # Loại bỏ khỏi danh sách khi kết nối bị ngắt
            with self.lock:
                if conn in self.managers:
                    self.managers.remove(conn)
            conn.close()
            print(f"[SERVER SCREEN] Manager disconnected (loop ended): {addr}")

    # def handle_manager(self, conn, addr):
    #     """Manager chỉ nhận ảnh"""
    #     print("[SERVER SCREEN] Manager connected:", addr)
    #     with self.lock:
    #         self.managers.append(conn)
        
    #     # CHẠY TRONG LUỒNG RIÊNG: Khởi tạo luồng receiver để giữ kết nối và xử lý ngắt
    #     threading.Thread(target=self._manager_receiver_loop, args=(conn, addr), daemon=True).start()

    def handle_manager(self, conn, addr):
        """Manager kết nối: 1. Đăng ký nhận stream, 2. Bắt đầu luồng gửi yêu cầu."""
        manager_ip = addr[0]
        print("[SERVER SCREEN] Manager connected:", manager_ip)
        
        # 1. Đăng ký Manager vào danh sách (Ban đầu xem client đầu tiên hoặc None)
        initial_ip = self.get_active_client_ips()[0] if self.get_active_client_ips() else None
        with self.managers_lock:
            # [socket_conn, desired_client_ip (str)]
            self.managers[manager_ip] = [conn, initial_ip] 
        
        # 2. Khởi tạo luồng lắng nghe lệnh chọn lọc từ Manager
        # Luồng này cần chạy daemon để không chặn luồng chính
        threading.Thread(target=self.handle_manager_request, args=(conn, manager_ip), daemon=True).start()
        
        # KHÔNG CẦN VÒNG LẶP NÀO NỮA: Luồng gửi (broadcast) sẽ chủ động gửi dữ liệu cho Manager này.
        # Luồng chính (run) sẽ thoát ngay, để tránh blocking.
        # Luồng _manager_receiver_loop (đã bị xóa) sẽ được thay thế bằng _periodic_broadcast_loop.

    def run(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # Nên thêm để tránh lỗi "Address already in use"
        
        try:
            server.bind((self.host, self.port))
            server.listen(5)
            print(f"[SERVER SCREEN] Listening on {self.host}:{self.port}")
        except Exception as e:
            print(f"[SERVER SCREEN] Failed to start server: {e}")
            return # Thoát nếu không bind được

        while True:
            try:
                conn, addr = server.accept()
                role = conn.recv(5).decode("utf-8")
                
                if role == "CLNT:":
                    threading.Thread(target=self.handle_client, args=(conn, addr), daemon=True).start()
                elif role == "MGR:":
                    # CHẠY MANAGER HANDLER TRONG LUỒNG RIÊNG
                    # Thay vì gọi trực tiếp self.handle_manager (sẽ bị chặn), ta chỉ cần gọi nó
                    # và logic thread được xử lý bên trong handle_manager
                    self.handle_manager(conn, addr)
                else:
                    print("[SERVER SCREEN] Unknown role, closing", addr)
                    conn.close()
            except socket.error:
                # Socket error thường xảy ra khi server.close() được gọi từ bên ngoài (graceful shutdown)
                break
            except Exception as e:
                print(f"[SERVER SCREEN] Accept loop general error: {e}")
                
        # Đóng socket lắng nghe khi thoát vòng lặp
        server.close()
        print("[SERVER SCREEN] ServerScreen listener stopped.")