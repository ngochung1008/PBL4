# remote_desktop_server.py

import socket
import threading
import sys
import time
import struct
import config
from server_transfer import ServerTransferHandler, close_all_transfer_connections
from server_screen import ServerScreen # Import ServerScreen để khởi động

class RemoteDesktopServer:
    def __init__(self, host="0.0.0.0"):
        self.host = host
        
        # Biến trạng thái
        self.is_running = True
        
        # Danh sách kết nối
        self.clients = [] 
        self.managers = [] 
        self.clients_lock = threading.Lock() 
        self.managers_lock = threading.Lock() 
        
        # Socket lắng nghe (khởi tạo trong setup_listeners)
        self.sm = None # Manager Control
        self.sc = None # Client Control
        self.st = None # Transfer
        
        # Cấu hình cổng
        self.CONTROL_PORT = config.CONTROL_PORT
        self.CLIENT_PORT = config.CLIENT_PORT
        self.SCREEN_PORT = config.SCREEN_PORT
        self.TRANSFER_PORT = config.TRANSFER_PORT
        
        # Luồng ServerScreen
        self.screen_thread = None

    # Server nhận lệnh từ Manager -> Forward cho Client.
    def handle_manager(self, conn, addr):
        print(f"[SERVER] Manager connected (Control): {addr}")

        # Thêm conn vào managers list
        with self.managers_lock: 
            self.managers.append(conn)

        try:
            while self.is_running:
                data = conn.recv(4096)
                if not data:
                    break
                
                # Forward cho tất cả Client
                with self.clients_lock:
                    for c in list(self.clients):
                        try:
                            c.sendall(data)
                        except:
                            try: self.clients.remove(c)
                            except: pass
                            
                # Forward tới các Manager khác (chủ yếu cho cursor_update phản hồi)
                with self.managers_lock:
                    for m in list(self.managers):
                        if m is conn: 
                            continue
                        try:
                            m.sendall(data)
                        except:
                            try: self.managers.remove(m)
                            except: pass
        finally:
            # Đảm bảo loại bỏ kết nối và đóng socket
            with self.managers_lock:
                if conn in self.managers:
                    self.managers.remove(conn)
            conn.close()
            print(f"[SERVER] Manager disconnected (Control): {addr}")

    # Server nhận tọa độ chuột từ Client -> Forward cho Manager.
    def handle_client(self, conn, addr):
        print(f"[SERVER] Client connected (Control): {addr}")

        # Thêm conn vào clients list
        with self.clients_lock:
            self.clients.append(conn)

        try:
            while self.is_running:
                data = conn.recv(4096)
                if not data:
                    break
                # Forward cho tất cả Manager
                with self.managers_lock:
                    for m in list(self.managers):
                        try:
                            m.sendall(data)
                        except:
                            try:
                                self.managers.remove(m)
                            except:
                                pass
        finally:
            with self.clients_lock:
                try:
                    self.clients.remove(conn)
                except ValueError:
                    pass
            conn.close()
            print(f"[SERVER] Client disconnected (Control): {addr}")

	# Lắng nghe và chạy vòng lặp 
    def _setup_listener(self, port):
        """Khởi tạo và lắng nghe trên một cổng TCP."""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((self.host, port))
        s.listen(5)
        return s

    def accept_loop(self, sock, handler_type, port_name):
        """Vòng lặp chấp nhận kết nối cho một cổng cụ thể."""
        print(f"[SERVER] Listening for {port_name} on port {sock.getsockname()[1]}")
        sock.settimeout(1.0)
        
        while self.is_running:
            try:
                conn, addr = sock.accept()
                
                if handler_type == "transfer":
                    # Khởi tạo ServerTransferHandler cho kết nối Transfer
                    threading.Thread(target=ServerTransferHandler(conn, addr).run, daemon=True).start()
                elif handler_type == "manager":
                    threading.Thread(target=self.handle_manager, args=(conn, addr), daemon=True).start()
                elif handler_type == "client":
                    threading.Thread(target=self.handle_client, args=(conn, addr), daemon=True).start()
                    
            except socket.error as e:
                if self.is_running:
                    if "closed" not in str(e):
                        print(f"[SERVER] Accept loop error ({port_name}): {e}")
                break # Thoát vòng lặp nếu socket bị đóng

    def start_control_server(self):
        """Khởi tạo các socket lắng nghe và bắt đầu các luồng chấp nhận kết nối."""
        try:
            # 1. Manager Control
            self.sm = self._setup_listener(self.CONTROL_PORT)
            threading.Thread(target=self.accept_loop, args=(self.sm, "manager", "manager control"), daemon=True).start()

            # 2. Client Control
            self.sc = self._setup_listener(self.CLIENT_PORT)
            threading.Thread(target=self.accept_loop, args=(self.sc, "client", "client control"), daemon=True).start()

            # 3. Transfer
            self.st = self._setup_listener(self.TRANSFER_PORT)
            threading.Thread(target=self.accept_loop, args=(self.st, "transfer", "transfer"), daemon=True).start()
            
        except Exception as e:
            print(f"[SERVER] Failed to start server listeners: {e}")
            self.close_all_connections()
            sys.exit(1)

    def start_screen_server(self):
        """Khởi động luồng ServerScreen."""
        screen_server = ServerScreen(self.host, self.SCREEN_PORT)
        self.screen_thread = threading.Thread(target=screen_server.run, daemon=True)
        self.screen_thread.start()
        print(f"[SERVER] Started screen relay on port {self.SCREEN_PORT}")

	# Hàm đóng tất cả kết nối đang hoạt động
    def close_all_connections(self):
        """Đóng tất cả kết nối và socket lắng nghe."""
        if not self.is_running:
            return

        self.is_running = False
        print("[SERVER] Closing all active connections...")

        # Đóng các kết nối đã thiết lập
        for lock, conn_list in [(self.managers_lock, self.managers), (self.clients_lock, self.clients)]:
            with lock:
                for conn in list(conn_list):
                    try: conn.shutdown(socket.SHUT_RDWR); conn.close()
                    except Exception: pass
                conn_list.clear()

        # Đóng các kết nối Transfer thông qua hàm utility
        close_all_transfer_connections() 

        # Đóng các socket lắng nghe
        for sock in [self.sm, self.sc, self.st]:
            if sock:
                try: sock.close()
                except Exception: pass
        
        # Đảm bảo luồng ServerScreen có thể thoát (giả định ServerScreen.run() sẽ thoát khi socket đóng)
        # Không gọi .join() vì sẽ chặn luồng chính.

    def run_server(self):
        """Khởi động toàn bộ Server."""
        self.start_control_server()
        self.start_screen_server()