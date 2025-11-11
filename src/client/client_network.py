# client/client_network.py
"file dùng"

import socket
from common_network.security_layer_tls import create_client_context, client_wrap_socket
from common_network.x224_handshake import X224Handshake
from common_network.tpkt_layer import TPKTLayer
from common_network.mcs_layer import MCSLite

class ClientNetwork:
    """Quản lý kết nối TLS + X224 + MCS với server"""
    def __init__(self, server_host, server_port, client_id, cafile="cert.pem"):
        self.server_host = server_host
        self.server_port = server_port
        self.client_id = client_id
        self.cafile = cafile
        self.sock = None
        self.ctx = create_client_context(cafile=cafile, check_hostname=False)
        self.mcs = MCSLite()
        self.tpkt = TPKTLayer()

    def connect(self):
        raw = socket.create_connection((self.server_host, self.server_port))
        self.sock = client_wrap_socket(raw, self.ctx, server_hostname="localhost")
        # Gửi handshake X224
        resp = X224Handshake.client_send_connect(self.sock, self.client_id)
        print(f"[NETWORK] Connected, handshake resp: {resp}")

    def send_pdu(self, channel_name, pdu_bytes):
        """Đóng gói theo MCS + TPKT rồi gửi"""
        data = self.mcs.pack(channel_name, pdu_bytes)
        tpkt_data = self.tpkt.pack(data)
        self.sock.sendall(tpkt_data)

    def recv_raw(self):
        """Nhận 1 TPKT frame thô (để xử lý input từ manager)"""
        hdr = self.sock.recv(4)
        if not hdr:
            return None
        _, _, length = self.tpkt.unpack_header(hdr)
        body = self.sock.recv(length - 4)
        return body

    def close(self):
        if self.sock:
            self.sock.close()
            self.sock = None
