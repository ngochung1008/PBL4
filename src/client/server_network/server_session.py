import socket
import threading
from common_network.pdu_parser import PDUParser
from common_network.tpkt_layer import TPKTLayer
from common_network.mcs_layer import MCSLayer  # lớp bạn tạo
from manager_client import ManagerClient

class ServerSession:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.stop = False
        self.parser = PDUParser()
        self.manager = ManagerClient("127.0.0.1", 8555)

    def start_accept_loop(self):
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.bind((self.host, self.port))
        srv.listen(5)
        print("[SERVER] Waiting for client...")

        while not self.stop:
            conn, addr = srv.accept()
            print(f"[SERVER] Client connected from {addr}")
            threading.Thread(target=self.handle_client, args=(conn,), daemon=True).start()

    def handle_client(self, conn):
        with conn:
            while not self.stop:
                header = conn.recv(4)
                if not header:
                    break
                version, reserved, total_len = TPKTLayer.unpack_header(header)
                body = conn.recv(total_len - 4)
                if not body:
                    break
                pdu = self.parser.parse(body)
                # Relay sang Manager
                self.manager.send_pdu(pdu)
