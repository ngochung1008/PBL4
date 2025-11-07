# File: server_network/tpkt_layer.py
import struct

TPKT_HEADER_FMT = ">BBH"
TPKT_OVERHEAD = 4
MAX_TPKT_LENGTH = 65535

class TPKTLayer:
    @staticmethod
    def pack(data_bytes: bytes) -> bytes:
        total_len = TPKT_OVERHEAD + len(data_bytes)
        if total_len > MAX_TPKT_LENGTH:
            raise ValueError(f"TPKT frame too large: {total_len}")
        return struct.pack(TPKT_HEADER_FMT, 0x03, 0x00, total_len) + data_bytes

    @staticmethod
    def unpack_header(hdr_bytes: bytes):
        return struct.unpack(TPKT_HEADER_FMT, hdr_bytes)