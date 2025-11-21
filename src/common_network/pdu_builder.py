# common_network/pdu_builder.py

import json
import struct
import time
from typing import List, Optional, Tuple
from common_network.constants import (
    PDU_TYPE_FULL, PDU_TYPE_RECT, PDU_TYPE_CONTROL, PDU_TYPE_INPUT, PDU_TYPE_CURSOR,
    PDU_TYPE_FILE_START, PDU_TYPE_FILE_CHUNK, PDU_TYPE_FILE_END, PDU_TYPE_FILE_ACK, PDU_TYPE_FILE_NAK,
    SHARE_CTRL_HDR_FMT,
    FRAGMENT_FLAG, FRAGMENT_HDR_FMT,
)

FRAGMENT_HDR_SIZE = struct.calcsize(FRAGMENT_HDR_FMT)
SHARE_HDR_SIZE = struct.calcsize(SHARE_CTRL_HDR_FMT)

class PDUBuilder:
    # xây dựng header chung cho PDU với seq, ts_ms, ptype, flags
    @staticmethod
    def _hdr(seq: int, ptype: int, flags: int = 0) -> bytes:
        ts_ms = int(time.time() * 1000)
        return struct.pack(SHARE_CTRL_HDR_FMT, seq, ts_ms, ptype, flags)
    
    """
    - Gọi PDUBuilder._hdr(...) để tạo header chung,
    - Đóng gói (stuct.pack) các thông tin cụ thể của từng loại PDU,
    - Nối (concatenate) tất cả lại: header_chung + header_riêng + payload_dữ_liệu 
    """

    # tạo pdu full frame 
    @staticmethod
    def build_full_frame_pdu(seq: int, jpeg_bytes: bytes, width: int, height: int, flags: int = 0) -> bytes:
        header = PDUBuilder._hdr(seq, PDU_TYPE_FULL, flags)
        frame_hdr = struct.pack(">III", width, height, len(jpeg_bytes))
        return header + frame_hdr + jpeg_bytes

    # tạo pdu rect frame
    @staticmethod
    def build_rect_frame_pdu(seq: int, jpeg_bytes: bytes, x: int, y: int, w: int, h: int, full_w: int, full_h: int, flags: int = 0) -> bytes:
        header = PDUBuilder._hdr(seq, PDU_TYPE_RECT, flags)
        rect_hdr = struct.pack(">IIIII", x, y, w, h, len(jpeg_bytes))
        full_dim = struct.pack(">II", full_w, full_h)
        return header + rect_hdr + full_dim + jpeg_bytes

    # tạo pdu control chung (ngắt kết nối, ping, ...)
    @staticmethod
    def build_control_pdu(seq: int, message_bytes: bytes) -> bytes:
        header = PDUBuilder._hdr(seq, PDU_TYPE_CONTROL, 0)
        msg_len = struct.pack(">I", len(message_bytes))
        return header + msg_len + message_bytes

    # tạo pdu input (chuột, bàn phím)
    @staticmethod
    def build_input_pdu(seq: int, input_obj: dict) -> bytes:
        body = json.dumps(input_obj).encode()
        header = PDUBuilder._hdr(seq, PDU_TYPE_INPUT, 0)
        msg_len = struct.pack(">I", len(body))
        return header + msg_len + body
    
    # tạo pdu con trỏ chuột
    @staticmethod
    @staticmethod
    def build_cursor_pdu(seq: int, x: int, y: int, cursor_shape_data: Optional[bytes] = None) -> bytes:
        header = PDUBuilder._hdr(seq, PDU_TYPE_CURSOR, 0)
        # Gói tọa độ (x, y) và độ dài dữ liệu hình dạng con trỏ (nếu có)
        # x (I - 4 bytes), y (I - 4 bytes), len(shape_data) (I - 4 bytes)
        shape_len = len(cursor_shape_data) if cursor_shape_data else 0
        cursor_hdr = struct.pack(">III", x, y, shape_len)
        if cursor_shape_data:
            return header + cursor_hdr + cursor_shape_data
        return header + cursor_hdr
    
    # tạo pdu bắt đầu truyền file
    @staticmethod
    def build_file_start(seq: int, filename: str, total_size: int, chunk_size: int = 32768, checksum: int = 0) -> bytes:
        header = PDUBuilder._hdr(seq, PDU_TYPE_FILE_START, 0)
        fn_bytes = filename.encode()
        fn_len = struct.pack(">H", len(fn_bytes))
        meta = struct.pack(">Q I I", total_size, chunk_size, checksum)
        return header + fn_len + fn_bytes + meta

    # tạo pdu chunk dữ liệu file
    @staticmethod
    def build_file_chunk(seq: int, offset: int, chunk_bytes: bytes) -> bytes:
        header = PDUBuilder._hdr(seq, PDU_TYPE_FILE_CHUNK, 0)
        hdr = struct.pack(">Q I", offset, len(chunk_bytes))
        return header + hdr + chunk_bytes

    # tạo pdu kết thúc truyền file
    @staticmethod
    def build_file_end(seq: int, checksum: int) -> bytes:
        header = PDUBuilder._hdr(seq, PDU_TYPE_FILE_END, 0)
        return header + struct.pack(">I", checksum)

    # tạo pdu xác nhận đã nhận file thành công
    @staticmethod
    def build_file_ack(seq: int, ack_offset: int) -> bytes:
        header = PDUBuilder._hdr(seq, PDU_TYPE_FILE_ACK, 0)
        return header + struct.pack(">Q", ack_offset)

    # tạo pdu thông báo lỗi khi nhận file
    @staticmethod
    def build_file_nak(seq: int, offset: int, reason: bytes = b"") -> bytes:
        header = PDUBuilder._hdr(seq, PDU_TYPE_FILE_NAK, 0)
        body = struct.pack(">Q I", offset, len(reason)) + reason
        return header + body

    # phân mảnh 1 PDU lớn thành nhiều fragment nhỏ hơn max_payload
    @staticmethod
    def fragmentize(pdu_bytes: bytes, max_payload: int) -> List[Tuple[int, bytes]]:
        import struct as _struct
        hdr_size = _struct.calcsize(SHARE_CTRL_HDR_FMT)
        if len(pdu_bytes) < hdr_size:
            raise ValueError("pdu_bytes too small")

        seq, ts_ms, ptype, flags = _struct.unpack(SHARE_CTRL_HDR_FMT, pdu_bytes[:hdr_size])
        body = pdu_bytes[hdr_size:]
        total_len = len(body)
        fragments = []
        offset = 0

        avail = max_payload - hdr_size - (_struct.calcsize(FRAGMENT_HDR_FMT))
        if avail <= 0:
            raise ValueError("max_payload too small for any fragment")

        while offset < total_len:
            chunk = body[offset: offset + avail]
            new_flags = flags | FRAGMENT_FLAG
            new_hdr = _struct.pack(SHARE_CTRL_HDR_FMT, seq, ts_ms, ptype, new_flags)
            frag_hdr = _struct.pack(FRAGMENT_HDR_FMT, offset, total_len)
            frag_bytes = new_hdr + frag_hdr + chunk
            fragments.append((offset, frag_bytes))
            offset += len(chunk)

        return fragments
