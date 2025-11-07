# client_network/tpkt_layer.py
import struct

TPKT_HEADER_FMT = ">BBH" # format struct — 1 byte version (0x03), 1 byte reserved, 2 bytes length (big-endian)
TPKT_OVERHEAD = 4
MAX_TPKT_LENGTH = 65535 # 2-byte limit 

# Lớp xử lý đóng gói dữ liệu theo chuẩn TPKT
class TPKTLayer:
    @staticmethod
    def pack(data_bytes: bytes) -> bytes:
        total_len = TPKT_OVERHEAD + len(data_bytes)
        if total_len > MAX_TPKT_LENGTH:
            raise ValueError(f"[CLIENT_NETWORK] TPKT frame quá lớn: {total_len}")
        tpkt_hdr = struct.pack(TPKT_HEADER_FMT, 0x03, 0x00, total_len)
        return tpkt_hdr + data_bytes