# File: manager_client.py
"""
Manager side client: connects to server, does X224 handshake, then receives TPKT frames
and feeds them to a callback for display.
"""
import socket
import threading
from server_network.x224_handshake import X224Handshake
from server_network.tpkt_layer import TPKTLayer
from server_network.pdu_parser import PDUParser

class ManagerClient:
    def __init__(self, host, port, manager_id='manager1'):
        self.host = host
        self.port = port
        self.manager_id = manager_id
        self.sock = None
        self.parser = PDUParser()
        self.running = False
        self.on_frame = None  # callback(pdu_dict)

    def connect(self):
        self.sock = socket.create_connection((self.host, self.port), timeout=10)
        # send X224 CONNECT
        payload = X224Handshake_connect_payload(self.manager_id)
        self.sock.sendall(payload)
        # read confirm
        hdr = X224Handshake.recv_all(self.sock, 4)
        ver, rsv, length = TPKTLayer.unpack_header(hdr)
        body = X224Handshake.recv_all(self.sock, length - 4)
        # ok - now start receiver
        self.running = True
        threading.Thread(target=self._recv_loop, daemon=True).start()

    def _recv_loop(self):
        try:
            while self.running:
                hdr = X224Handshake.recv_all(self.sock, 4)
                ver, rsv, length = TPKTLayer.unpack_header(hdr)
                body = X224Handshake.recv_all(self.sock, length - 4)
                # parse pdu
                try:
                    pdu = self.parser.parse_pdu(body)
                    if self.on_frame:
                        self.on_frame(pdu)
                except Exception:
                    continue
        except Exception as e:
            print("[MANAGER] recv loop error:", e)
            self.running = False

    def close(self):
        self.running = False
        try:
            self.sock.close()
        except Exception:
            pass


def X224Handshake_connect_payload(client_id: str):
    # build TPKT header + CONNECT_MAGIC:id
    from server_network.x224_handshake import CONNECT_MAGIC
    import struct
    body = CONNECT_MAGIC + b":" + client_id.encode()
    return struct.pack(TPKTLayer_format(), 0x03, 0x00, 4 + len(body)) + body


def TPKTLayer_format():
    return ">BBH"