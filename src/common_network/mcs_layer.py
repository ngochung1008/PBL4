# common_network/mcs_layer.py

import struct
import logging
from collections import defaultdict
from typing import Optional, Dict, Tuple
from .constants import MCS_HDR_FMT, MCS_HDR_SIZE, MAX_CHANNEL_BUFFER

log = logging.getLogger(__name__)
class MCSLite:
    def __init__(self):
        self.buffer = bytearray() # buffer chung, nhận dữ liệu thô từ TCP (qua TPKT)
        self.channel_buffers: Dict[int, bytearray] = defaultdict(bytearray) # buffer riêng cho từng channel_id, key là channel_id, value là bytearray
        self._channel_names: Dict[int, str] = {} # ánh xạ ID sang tên kênh

    # đóng gói PDU với header MCS (channel_id (H), length (H)) + payload
    @staticmethod
    def build(channel_id: int, payload: bytes) -> bytes:
        length = len(payload)
        header = struct.pack(MCS_HDR_FMT, channel_id, length)
        return header + payload

    # thêm dữ liệu thô (từ TPKT) vào buffer để giải mã
    def feed(self, data: bytes) -> None:
        self.buffer.extend(data)
        self._process_buffer()

    # giải mã 1 PDU từ buffer, trả về (channel_id, payload)
    # def unpack(self) -> Tuple[int, bytes]:
    #     if len(self.buffer) < MCS_HDR_SIZE:
    #         raise ValueError("not enough data for mcs header")
    #     channel_id = struct.unpack(MCS_HDR_FMT, self.buffer[:MCS_HDR_SIZE])[0]
    #     payload = bytes(self.buffer[MCS_HDR_SIZE:])
    #     self.buffer.clear()
    #     return channel_id, payload

    # vòng lặp xử lý buffer thô để tách các MCS frame
    def _process_buffer(self) -> None:
        while True:
            if len(self.buffer) < MCS_HDR_SIZE:
                break 

            # đọc header (channel_id và length)
            channel_id, payload_len = struct.unpack_from(MCS_HDR_FMT, self.buffer)
            
            frame_total_len = MCS_HDR_SIZE + payload_len
            if len(self.buffer) < frame_total_len:
                break

            # trích xuất payload khi đã đủ data
            payload_start = MCS_HDR_SIZE
            payload_end = frame_total_len
            payload = self.buffer[payload_start:payload_end]

            # đưa payload vào buffer của kênh tương ứng
            ch_buf = self.channel_buffers[channel_id]
            if len(ch_buf) + payload_len > MAX_CHANNEL_BUFFER:
                # chống overflow, xóa buffer của kênh này và báo lỗi
                log.error(f"Channel {channel_id} buffer overflow. Dropping data.")
                ch_buf.clear()
            
            ch_buf.extend(payload)

            # xóa frame đã xử lý khỏi buffer chung
            del self.buffer[:frame_total_len]

    # lấy PDU tiếp theo
    # def next_pdu(self) -> Tuple[Optional[int], Optional[bytes]]:
    #     try:
    #         ch, payload = self.unpack()
    #         return ch, payload
    #     except ValueError:
    #         return None, None

    # Lấy và xóa toàn bộ dữ liệu từ buffer của một kênh cụ thể
    def read_channel(self, channel_id: int) -> Optional[bytes]:
        ch_buf = self.channel_buffers.get(channel_id)
        if not ch_buf:
            return None 

        payload_data = bytes(ch_buf)
        ch_buf.clear()
        return payload_data
    
    # kiểm tra xem buffer của kênh có bao nhiêu data chờ xử lý
    def get_channel_data_size(self, channel_id: int) -> int:
        return len(self.channel_buffers.get(channel_id, b''))

    # lấy tên kênh từ channel_id từ self._channel_names
    def get_channel_name(self, channel_id: int) -> Optional[str]:
        return self._channel_names.get(channel_id)

    # đặt tên kênh cho channel_id trong self._channel_names
    def set_channel_name(self, channel_id: int, name: str) -> None:
        self._channel_names[channel_id] = name
