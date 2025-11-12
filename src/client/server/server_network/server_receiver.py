import threading
from client.server.server_network.server_transport import ServerTransport
from client.common_network.pdu_parser import PDUParser

class ServerReceiver(threading.Thread):
    """Luồng nhận dữ liệu từ 1 client."""

    def __init__(self, session, on_pdu_callback):
        super().__init__(daemon=True)
        self.session = session
        self.on_pdu = on_pdu_callback
        self.parser = PDUParser()

    def run(self):
        sock = self.session.sock
        try:
            while self.session.alive:
                # ServerTransport.recv trả về "body" (payload của TPKT)
                body = ServerTransport.recv(sock)
                # body ở đây chính là MCS packet (2-byte channel id + PDU payload)
                pdu = self.parser.parse_with_mcs(body)
                # Chuyển cả parsed pdu và raw payload để on_pdu xử lý/forward.
                self.on_pdu(self.session, pdu, body)
        except Exception as e:
            print(f"[Receiver {self.session.client_id}] disconnected:", e)
            self.session.close()
