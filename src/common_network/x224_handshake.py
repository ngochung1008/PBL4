# common_network/x224_handshake.py

import struct
from common_network.constants import TPKT_HEADER_FMT

CONNECT_MAGIC = b"X224_CONNECT_V1"
CONFIRM_MAGIC = b"X224_CONFIRM_V1"

class X224Handshake:
    # nhận chính xác n bytes từ socket
    @staticmethod
    def recv_all(sock, n, timeout=10):
        sock.settimeout(timeout)
        data = bytearray()
        while len(data) < n:
            chunk = sock.recv(n - len(data))
            if not chunk:
                raise ConnectionError("socket closed")
            data.extend(chunk)
        return bytes(data)

    # gửi yêu cầu kết nối từ client và chờ phản hồi từ server
    @staticmethod
    def client_send_connect(sock, client_id: str, timeout=10):
        body = CONNECT_MAGIC + b":" + client_id.encode() # b"X224_CONNECT_V1:MyComputerName
        hdr = struct.pack(TPKT_HEADER_FMT, 0x03, 0x00, 4 + len(body))
        sock.sendall(hdr + body)
        sock.settimeout(timeout)

        hdr = X224Handshake.recv_all(sock, 4, timeout)
        ver, rsv, length = struct.unpack(TPKT_HEADER_FMT, hdr)

        if length > 4096:
            raise ValueError("X224 handshake response too large")

        body = X224Handshake.recv_all(sock, length - 4, timeout)
        return body

    # xử lý yêu cầu kết nối từ client và gửi phản hồi từ server
    @staticmethod
    def server_do_handshake(sock, timeout=10):
        sock.settimeout(timeout)

        hdr = X224Handshake.recv_all(sock, 4, timeout)
        ver, rsv, length = struct.unpack(TPKT_HEADER_FMT, hdr)

        if length > 4096:
            try:
                bad = b"BAD_TOO_LARGE"
                tpkt = struct.pack(TPKT_HEADER_FMT, 0x03, 0x00, 4 + len(bad)) + bad
                sock.sendall(tpkt)
            except:
                pass
            return False, None

        body = X224Handshake.recv_all(sock, length - 4, timeout)
        if not body.startswith(CONNECT_MAGIC + b":"):
            try:
                bad = b"BAD_MAGIC"
                tpkt = struct.pack(TPKT_HEADER_FMT, 0x03, 0x00, 4 + len(bad)) + bad
                sock.sendall(tpkt)
            except:
                pass
            return False, None

        _, rest = body.split(b":", 1)
        client_id = rest.decode(errors="ignore")

        resp = CONFIRM_MAGIC + b":OK"
        tpkt = struct.pack(TPKT_HEADER_FMT, 0x03, 0x00, 4 + len(resp)) + resp
        sock.sendall(tpkt)

        return True, client_id
