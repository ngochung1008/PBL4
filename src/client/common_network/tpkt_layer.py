# common_network/tpkt_layer.py
import struct

TPKT_HEADER_FMT = ">BBH"
TPKT_OVERHEAD = 4
MAX_TPKT_LENGTH = 65535

class TPKTLayer:
    @staticmethod
    def pack(body: bytes) -> bytes:
        total_len = TPKT_OVERHEAD + len(body)
        if total_len > MAX_TPKT_LENGTH:
            raise ValueError(f"TPKT too large: {total_len}")
        return struct.pack(TPKT_HEADER_FMT, 0x03, 0x00, total_len) + body

    @staticmethod
    def unpack_header(hdr: bytes):
        return struct.unpack(TPKT_HEADER_FMT, hdr)
