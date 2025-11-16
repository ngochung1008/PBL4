# common_network/tpkt_layer.py
import struct

from .constants import (
    TPKT_HEADER_FMT, 
    TPKT_OVERHEAD, 
    MAX_TPKT_LENGTH
)

# Lớp TPKT bọc thêm/ giải mã header cho các gói logic do PDUBuilder tạo ra để phân biệt từng gói khi gửi qua TCP
class TPKTLayer:
    # đóng gói dữ liệu body (PDU được bọc bởi MCS) thành gói TPKT hoàn chỉnh
    @staticmethod
    def pack(body: bytes) -> bytes:
        total_len = TPKT_OVERHEAD + len(body)
        if total_len > MAX_TPKT_LENGTH:
            raise ValueError(f"TPKT too large: {total_len}")
        return struct.pack(TPKT_HEADER_FMT, 0x03, 0x00, total_len) + body

    # dùng để đọc header (TPKT) từ socket trước khi đọc phần thân (body)
    @staticmethod
    def unpack_header(hdr: bytes):
        return struct.unpack(TPKT_HEADER_FMT, hdr)
