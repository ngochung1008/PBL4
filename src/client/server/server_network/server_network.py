import socket
import threading
from client.common_network.x224_handshake import X224Handshake
from client.server.server_network.server_session import ServerSession
from client.server.server_network.server_receiver import ServerReceiver

class ServerNetwork:
    """Quản lý kết nối đến từ cả client và manager."""

    def __init__(self, host, port, on_client_pdu, on_manager_conn):
        self.host = host
        self.port = port
        self.on_client_pdu = on_client_pdu
        self.on_manager_conn = on_manager_conn

    def start(self):
        threading.Thread(target=self._accept_loop, daemon=True).start()

    def _accept_loop(self):
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.bind((self.host, self.port))
        srv.listen(10)
        print(f"[ServerNetwork] Listening on {self.host}:{self.port}")

        while True:
            sock, addr = srv.accept()
            ok, client_id = X224Handshake.server_do_handshake(sock)
            if not ok:
                print("[ServerNetwork] Bad handshake from", addr)
                sock.close()
                continue

            if client_id.startswith("manager"):
                print(f"[ServerNetwork] Manager connected: {client_id}")
                self.on_manager_conn(client_id, sock)
            else:
                print(f"[ServerNetwork] Client connected: {client_id}")
                session = ServerSession(sock, addr, client_id)
                recv_thread = ServerReceiver(session, self.on_client_pdu)
                recv_thread.start()
