# common_network/pdu_builder.py

import struct
import time
import json

from .constants import (
    PDU_TYPE_FULL, PDU_TYPE_RECT, PDU_TYPE_CONTROL, PDU_TYPE_INPUT,
    SHARE_CTRL_HDR_FMT
)

# Lớp đóng gói thành PDU để truyền qua mạng
class PDUBuilder:
    # tạo header
    @staticmethod
    def _hdr(seq, ptype, flags=0):
        ts_ms = int(time.time() * 1000)
        return struct.pack(SHARE_CTRL_HDR_FMT, seq, ts_ms, ptype, flags)

    # tạo gói dùng để gửi toàn bộ khung hình (full frame) (client->server hoặc server->manager)
    # jpeg_bytes: nội dung ảnh nén JPEG -> len(jpeg_bytes): kích thước ảnh; width + height: kích thước khung hình
    @staticmethod
    def build_full_frame_pdu(seq, jpeg_bytes, width, height, flags=0):
        header = PDUBuilder._hdr(seq, PDU_TYPE_FULL, flags)
        frame_hdr = struct.pack(">III", width, height, len(jpeg_bytes))
        return header + frame_hdr + jpeg_bytes

    # tạo gói dùng để gửi 1 phần vùng thay đổi (rectangle update)
    @staticmethod
    def build_rect_frame_pdu(seq, jpeg_bytes, x, y, w, h, full_w, full_h, flags=0):
        header = PDUBuilder._hdr(seq, PDU_TYPE_RECT, flags)
        rect_hdr = struct.pack(">IIIII", x, y, w, h, len(jpeg_bytes))
        full_dim = struct.pack(">II", full_w, full_h)
        return header + rect_hdr + full_dim + jpeg_bytes

    # tạo gói gửi lệnh điều khiển (control message)
    @staticmethod
    def build_control_pdu(seq, message_bytes):
        header = PDUBuilder._hdr(seq, PDU_TYPE_CONTROL, 0)
        msg_len = struct.pack(">I", len(message_bytes))
        return header + msg_len + message_bytes

    # tạo gói gửi dữ liệu đầu vào (input event) - chuột, bàn phím
    @staticmethod
    def build_input_pdu(seq, input_obj):
        body = json.dumps(input_obj).encode()
        header = PDUBuilder._hdr(seq, PDU_TYPE_INPUT, 0)
        msg_len = struct.pack(">I", len(body))
        return header + msg_len + body
