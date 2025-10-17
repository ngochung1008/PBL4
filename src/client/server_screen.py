# server_screen.py
import socket
import struct
import threading

class ServerScreen:
    def __init__(self, host="0.0.0.0", port=5000):
        self.host = host
        self.port = port
        self.managers = []  # list manager connections
        self.lock = threading.Lock()

    def broadcast_to_managers(self, data):
        """Gửi ảnh tới tất cả managers"""
        with self.lock:
            for m in list(self.managers):
                try:
                    m.sendall(data)
                except:
                    print("[SERVER SCREEN] Manager disconnected")
                    self.managers.remove(m)
    
    def _recv_exact(self, conn, n):
        data = b""
        while len(data) < n:
            chunk = conn.recv(n - len(data))
            if not chunk:
                raise ConnectionError("Lost connection")
            data += chunk
        return data

    def handle_client(self, conn, addr):
        """Nhận dữ liệu màn hình từ Client và phát lại cho managers"""
        print("[SERVER SCREEN] Client stream connected:", addr)
        try:
            while True:
                # Nhận header 12 byte: width(4), height(4), length(4)
                header = self._recv_exact(conn, 12)
                w, h, length = struct.unpack(">III", header)

                payload = self._recv_exact(conn, length)

                # Gửi lại cho managers (gồm header + ảnh)
                self.broadcast_to_managers(header + payload)
        except Exception as e:
            print("[SERVER SCREEN] Client error:", e)
        finally:
            conn.close()
            print("[SERVER SCREEN] Client disconnected")

    def handle_manager(self, conn, addr):
        """Manager chỉ nhận ảnh"""
        print("[SERVER SCREEN] Manager connected:", addr)
        with self.lock:
            self.managers.append(conn)

    def run(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind((self.host, self.port))
        server.listen(5)
        print(f"[SERVER SCREEN] Listening on {self.host}:{self.port}")

        while True:
            conn, addr = server.accept()
            # Trường hợp đầu tiên là Client gửi màn hình
            # Mình phân biệt bằng handshake ban đầu
            role = conn.recv(5).decode("utf-8")
            if role == "CLNT:":
                threading.Thread(target=self.handle_client, args=(conn, addr), daemon=True).start()
            elif role == "MGR:":  
                self.handle_manager(conn, addr)
            else:
                print("[SERVER SCREEN] Unknown role, closing", addr)
                conn.close()