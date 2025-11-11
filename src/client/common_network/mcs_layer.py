# common_network/mcs_layer.py

import struct

MCS_HEADER_FMT = ">H"  # 2 byte channel_id
MCS_OVERHEAD = 2

class MCSLite:
    def __init__(self):
        # ánh xạ các loại dữ liệu sang ID kênh
        self.channels = {
            "screen": 1001,   # gói hình ảnh
            "control": 1002,  # gói điều khiển (start/stop/share)
            "input": 1003,    # gói chuột, bàn phím
            "file": 1004,     # gói truyền file
        }

    def get_channel_id(self, name: str) -> int:
        return self.channels.get(name, 1001)
    
    def get_channel_name(self, ch_id: int) -> str:
        for name, cid in self.channels.items():
            if cid == ch_id:
                return name
        return "unknown"

    def pack(self, channel_name: str, pdu_data: bytes) -> bytes:
        ch_id = self.get_channel_id(channel_name)
        return struct.pack(MCS_HEADER_FMT, ch_id) + pdu_data

    def unpack(self, data: bytes):
        if len(data) < MCS_OVERHEAD:
            raise ValueError("MCS packet too small")
        ch_id, = struct.unpack(MCS_HEADER_FMT, data[:MCS_OVERHEAD])
        payload = data[MCS_OVERHEAD:]
        return ch_id, payload
