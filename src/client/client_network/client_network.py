import socket
from client.common_network.x224_handshake import X224Handshake, CONFIRM_MAGIC

class ClientNetwork:
    """Kết nối tới server và thực hiện handshake."""

    def __init__(self, host, port, client_id="client1"):
        self.host = host
        self.port = port
        self.client_id = client_id
        self.sock = None

    def connect(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            resp = X224Handshake.client_send_connect(self.sock, self.client_id)
            if not resp:
                return False
            if resp.startswith(CONFIRM_MAGIC):
                return True
            else:
                print("[ClientNetwork] Handshake reply unexpected:", resp)
                return False
        except Exception as e:
            print("[ClientNetwork] Connection failed:", e)
            return False
