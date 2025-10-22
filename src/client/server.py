# server.py

import socket
import threading
import struct
import io
import sys
import time
from PIL import Image
from server_screen import ServerScreen  
import config

CONTROL_PORT = config.CONTROL_PORT
CLIENT_PORT = config.CLIENT_PORT
SCREEN_PORT = config.SCREEN_PORT

clients = []  # list kết nối client
managers = []  # list kết nối manager
clients_lock = threading.Lock()  
managers_lock = threading.Lock() 
_SERVER_RUNNING = True

# Server nhận lệnh từ Manager -> Forward cho Client (để thực thi lệnh).
def handle_manager(conn, addr):
    # Hàm này forward lệnh từ Manager -> Client 
    print("[SERVER] Manager connected:", addr)

    # Thêm conn vào managers list
    with managers_lock:  
        managers.append(conn)

    try:
        while True:
            data = conn.recv(4096)
            if not data:
                break
            # forward cho tất cả client
            with clients_lock:
                for c in list(clients):
                    try:
                        c.sendall(data)
                    except:
                        try:
                            clients.remove(c)
                        except:
                            pass
            # forward tới các manager khác
            with managers_lock:
                for m in list(managers):
                    if m is conn:
                        continue
                    try:
                        m.sendall(data)
                    except:
                        try:
                            managers.remove(m)
                        except:
                            pass
    finally:
        # Đảm bảo loại bỏ kết nối và đóng socket
        with managers_lock:
            if conn in managers:
                managers.remove(conn)
        conn.close()
        print(f"[SERVER] Manager disconnected: {addr}")

# Server nhận tọa độ chuột từ Client -> Forward cho Manager (để hiển thị chấm đỏ).
def handle_client(conn, addr):
    print("[SERVER] Client connected:", addr)

    # Thêm conn vào clients list
    with clients_lock:
        clients.append(conn)
    
    try:
        while True:
            data = conn.recv(4096)
            if not data:
                break
            # Khi client gửi (ví dụ cursor_update), forward cho tất cả manager
            with managers_lock:
                for m in list(managers):
                    try:
                        m.sendall(data)
                    except:
                        try:
                            managers.remove(m)
                        except:
                            pass
    finally:
        # Đảm bảo loại bỏ kết nối và đóng socket
        with clients_lock:
            try:
                clients.remove(conn)
            except ValueError:
                pass
        conn.close()
        print(f"[SERVER] Client disconnected: {addr}")

# Hàm đóng tất cả kết nối đang hoạt động
def close_all_connections():
    global _SERVER_RUNNING
    _SERVER_RUNNING = False
    
    # Đóng các kết nối Manager
    with managers_lock:
        for m in managers:
            try:
                m.shutdown(socket.SHUT_RDWR) # Cố gắng đóng sạch sẽ
                m.close()
            except Exception:
                pass
        managers.clear()
        
    # Đóng các kết nối Client
    with clients_lock:
        for c in clients:
            try:
                c.shutdown(socket.SHUT_RDWR)
                c.close()
            except Exception:
                pass
        clients.clear()
    
# Hàm lắng nghe chính (sử dụng cờ _SERVER_RUNNING)
def start_control_server():
    global sm, sc # Khai báo global để có thể đóng sau
    
    # Lắng nghe Manager input
    sm = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sm.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # Cho phép tái sử dụng địa chỉ
    sm.bind(("0.0.0.0", CONTROL_PORT))
    sm.listen(5)
    print(f"[SERVER] Listening for manager on port {CONTROL_PORT}")

    # Lắng nghe Client input
    sc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sc.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) 
    sc.bind(("0.0.0.0", CLIENT_PORT))
    sc.listen(5)
    print(f"[SERVER] Listening for clients on port {CLIENT_PORT}")

    def accept_loop(sock, handler):
        while _SERVER_RUNNING:
            try:
                conn, addr = sock.accept()
                threading.Thread(target=handler, args=(conn, addr), daemon=True).start()
            except socket.error as e:
                if _SERVER_RUNNING:
                    print(f"[SERVER] Accept loop error: {e}")
                break

    threading.Thread(target=accept_loop, args=(sm, handle_manager), daemon=True).start()
    threading.Thread(target=accept_loop, args=(sc, handle_client), daemon=True).start()

# Main block để xử lý tín hiệu đóng
if __name__ == "__main__":
    import signal
    
    def signal_handler(sig, frame):
        print('\n[SERVER] Shutdown signal received. Closing all connections.')
        close_all_connections()
        sm.close() # Đóng socket lắng nghe
        sc.close()
        # Chờ ServerScreen đóng (ServerScreen.run() thường là blocking)
        sys.exit(0)

    # Bắt tín hiệu Ctrl+C (SIGINT)
    signal.signal(signal.SIGINT, signal_handler) 
    
    start_control_server()
    
    # Chạy ServerScreen (relay frame)
    screen_server = ServerScreen("0.0.0.0", SCREEN_PORT)
    
    # Chạy ServerScreen trong một luồng để luồng chính có thể lắng nghe tín hiệu
    threading.Thread(target=screen_server.run, daemon=True).start() 
    
    # GIỮ LUỒNG CHÍNH CHẠY: để bắt tín hiệu Ctrl+C
    while True:
        time.sleep(1)