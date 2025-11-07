# common_network/x224_handshake.py
import struct

TPKT_HEADER_FMT = ">BBH"
CONNECT_MAGIC = b"X224_CONNECT_V1"
CONFIRM_MAGIC = b"X224_CONFIRM_V1"

class X224Handshake:
    @staticmethod
    def recv_all(sock, n):
        data = bytearray()
        while len(data) < n:
            chunk = sock.recv(n - len(data))
            if not chunk:
                raise ConnectionError("socket closed")
            data.extend(chunk)
        return bytes(data)

    @staticmethod
    def client_send_connect(sock, client_id: str, timeout=10):
        body = CONNECT_MAGIC + b":" + client_id.encode()
        hdr = struct.pack(TPKT_HEADER_FMT, 0x03, 0x00, 4 + len(body))
        sock.sendall(hdr + body)
        sock.settimeout(timeout)
        # read confirm
        hdr = X224Handshake.recv_all(sock, 4)
        ver, rsv, length = struct.unpack(TPKT_HEADER_FMT, hdr)
        body = X224Handshake.recv_all(sock, length - 4)
        return body

    @staticmethod
    def server_do_handshake(sock, timeout=10):
        sock.settimeout(timeout)
        hdr = X224Handshake.recv_all(sock, 4)
        ver, rsv, length = struct.unpack(TPKT_HEADER_FMT, hdr)
        body = X224Handshake.recv_all(sock, length - 4)
        if not body.startswith(CONNECT_MAGIC + b":"):
            # send BAD
            try:
                bad = b"BAD"
                tpkt = struct.pack(TPKT_HEADER_FMT, 0x03, 0x00, 4 + len(bad)) + bad
                sock.sendall(tpkt)
            except Exception:
                pass
            return False, None
        # parse id
        _, rest = body.split(b":", 1)
        client_id = rest.decode(errors="ignore")
        resp = CONFIRM_MAGIC + b":OK"
        tpkt = struct.pack(TPKT_HEADER_FMT, 0x03, 0x00, 4 + len(resp)) + resp
        sock.sendall(tpkt)
        return True, client_id
