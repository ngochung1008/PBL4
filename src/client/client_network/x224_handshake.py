# client_network/x224_handshake.py
import struct

TPKT_HEADER_FMT = ">BBH"
# Mô phỏng handshake X.224: Client gửi CONNECT, Server trả CONFIRM
class X224Handshake:
    CONNECT_MAGIC = b"X224_CONNECT_V1"
    CONFIRM_MAGIC = b"X224_CONFIRM_V1"

    def __init__(self, client_id, timeout=10):
        self.client_id = client_id
        self.timeout = timeout

    def recv_all(sock, n):
        data = bytearray()
        while len(data) < n:
            chunk = sock.recv(n - len(data))
            if not chunk:
                raise ConnectionError("Socket closed")
            data.extend(chunk)
        return bytes(data)


    def do_handshake(self, sock):
        payload = self.CONNECT_MAGIC + b":" + self.client_id.encode()
        tpkt = struct.pack(TPKT_HEADER_FMT, 0x03, 0x00, 4 + len(payload))
        sock.sendall(tpkt + payload)

        sock.settimeout(self.timeout)
        hdr = X224Handshake.recv_all(sock, 4)
        if len(hdr) < 4:
            return False
        ver, rsv, length = struct.unpack(TPKT_HEADER_FMT, hdr)
        body = sock.recv(length - 4)
        return body.startswith(self.CONFIRM_MAGIC)
