import socket
from client.common_network.x224_handshake import X224Handshake, CONFIRM_MAGIC
from client.manager.manager_network.manager_transport import ManagerTransport

class ManagerClient:
    """Kết nối tới server như 1 manager."""

    def __init__(self, host, port, manager_id="manager1"):
        self.host = host
        self.port = port
        self.manager_id = manager_id
        self.sock = None

    def connect(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            # use client_send_connect and check response for CONFIRM_MAGIC
            resp = X224Handshake.client_send_connect(self.sock, self.manager_id)
            if not resp:
                return False
            # resp is bytes body returned from server; confirm it contains confirm magic
            if resp.startswith(CONFIRM_MAGIC):
                return True
            else:
                print("[ManagerClient] Handshake reply unexpected:", resp)
                return False
        except Exception as e:
            print("[ManagerClient] Connect error:", e)
            return False

    def recv_loop(self, on_data_callback):
        while True:
            data = ManagerTransport.recv(self.sock)
            on_data_callback(data)
