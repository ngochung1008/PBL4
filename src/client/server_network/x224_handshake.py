# File: server_network/x224_handshake.py
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
                raise ConnectionError("Socket closed")
            data.extend(chunk)
        return bytes(data)

    @staticmethod
    def server_do_handshake(sock, timeout=10):
        sock.settimeout(timeout)
        # read TPKT header
        hdr = X224Handshake.recv_all(sock, 4)
        ver, rsv, length = struct.unpack(TPKT_HEADER_FMT, hdr)
        body = X224Handshake.recv_all(sock, length - 4)
        # body expected to be CONNECT_MAGIC + b":" + client_id
        if not body.startswith(CONNECT_MAGIC + b":"):
            try:
                # send a negative confirm
                tpkt = struct.pack(TPKT_HEADER_FMT, 0x03, 0x00, 4 + len(b"BAD")) + b"BAD"
                sock.sendall(tpkt)
            except Exception:
                pass
            return False
        # parse id
        _, rest = body.split(b":", 1)
        client_id = rest.decode(errors='ignore')
        print(f"[SERVER] X224 CONNECT from id={client_id}")
        # send confirm
        resp = CONFIRM_MAGIC + b":" + b"OK"
        tpkt = struct.pack(TPKT_HEADER_FMT, 0x03, 0x00, 4 + len(resp)) + resp
        sock.sendall(tpkt)
        return True