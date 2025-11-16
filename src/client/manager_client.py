import socket
import struct
from common_network.tpkt_layer import TPKTLayer

class ManagerClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = None

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))
        print(f"[MANAGER] Connected to {self.host}:{self.port}")

    def send_pdu(self, pdu):
        """Gửi gói PDU (đã build sẵn) đến manager."""
        if self.sock is None:
            self.connect()
        packet = TPKTLayer.pack(pdu)
        self.sock.sendall(packet)
