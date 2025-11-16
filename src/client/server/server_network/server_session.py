import threading
import socket
from client.server.server_network.server_transport import ServerTransport

class ServerSession:
    """Lưu thông tin và hỗ trợ gửi gói đến client."""

    def __init__(self, sock: socket.socket, addr, client_id: str):
        self.sock = sock
        self.addr = addr
        self.client_id = client_id
        self.alive = True
        self.lock = threading.Lock()

    def send(self, data: bytes):
        if not self.alive:
            return
        try:
            with self.lock:
                ServerTransport.send(self.sock, data)
        except Exception as e:
            print(f"[Session {self.client_id}] send error:", e)
            self.close()

    def close(self):
        if self.alive:
            try:
                self.sock.close()
            except:
                pass
            self.alive = False
            print(f"[Session {self.client_id}] closed.")
