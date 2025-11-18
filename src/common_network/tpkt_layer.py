# common_network/tpkt_layer.py

import struct
import time
from common_network.constants import TPKT_HEADER_FMT, TPKT_OVERHEAD, MAX_TPKT_LENGTH

class TPKTLayer:
    # nhận chính xác n bytes từ socket 
    @staticmethod
    def recv_exact(sock, n, recv_fn=None, timeout=10):
        sock.settimeout(timeout)
        if recv_fn is None:
            recv_fn = sock.recv

        data = bytearray()
        start = time.time()
        while len(data) < n:
            if time.time() - start > timeout:
                raise TimeoutError("TPKT recv_exact timeout")

            chunk = recv_fn(n - len(data))
            if not chunk:
                raise ConnectionError("socket closed during recv_exact")
            data.extend(chunk)
        return bytes(data)

    # đóng gói body (là PDU của lớp MCS [channel_id][payload]) vào TPKT header
    @staticmethod
    def pack(body: bytes) -> bytes:
        total_len = TPKT_OVERHEAD + len(body)
        if total_len > MAX_TPKT_LENGTH:
            raise ValueError(f"TPKT too large: {total_len}")
        return struct.pack(TPKT_HEADER_FMT, 0x03, 0x00, total_len) + body

    # gỡ TPKT header, trả về (version, reserved, length)
    @staticmethod
    def unpack_header(hdr: bytes):
        return struct.unpack(TPKT_HEADER_FMT, hdr)

    # đọc một TPKT đầy đủ từ socket, trả về body (PDU của lớp MCS)
    @staticmethod
    def recv_one(sock, recv_fn=None, timeout=10):
        hdr = TPKTLayer.recv_exact(sock, TPKT_OVERHEAD, recv_fn=recv_fn, timeout=timeout)
        ver, rsv, total_len = struct.unpack(TPKT_HEADER_FMT, hdr)

        if total_len < TPKT_OVERHEAD or total_len > MAX_TPKT_LENGTH:
            raise ValueError(f"Invalid TPKT total_len {total_len}")

        body_len = total_len - TPKT_OVERHEAD
        body = TPKTLayer.recv_exact(sock, body_len, recv_fn=recv_fn, timeout=timeout)
        return body
