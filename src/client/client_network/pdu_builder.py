# client_network/pdu_builder.py
import struct
import time

PDU_TYPE_FULL = 1
PDU_TYPE_RECT = 2
PDU_TYPE_CONTROL = 3
PDU_TYPE_INPUT = 4
SHARE_CTRL_HDR_FMT = ">IQBB"  # seq, timestamp_ms, type, flags

# Đóng gói dữ liệu gửi đi: FullFrame, RectFrame, ControlMessage
class PDUBuilder:
    @staticmethod
    def build_full_frame_pdu(seq, jpeg_bytes, width, height, flags=0):
        ts_ms = int(time.time() * 1000)
        header = struct.pack(SHARE_CTRL_HDR_FMT, seq, ts_ms, PDU_TYPE_FULL, flags)
        frame_hdr = struct.pack(">III", width, height, len(jpeg_bytes))
        return header + frame_hdr + jpeg_bytes

    @staticmethod
    def build_rect_frame_pdu(seq, jpeg_bytes, x, y, w, h, full_w, full_h, flags=0):
        ts_ms = int(time.time() * 1000)
        header = struct.pack(SHARE_CTRL_HDR_FMT, seq, ts_ms, PDU_TYPE_RECT, flags)
        rect_hdr = struct.pack(">IIIII", x, y, w, h, len(jpeg_bytes))
        full_dim = struct.pack(">II", full_w, full_h)
        return header + rect_hdr + full_dim + jpeg_bytes

    @staticmethod
    def build_control_pdu(seq, message_bytes):
        ts_ms = int(time.time() * 1000)
        header = struct.pack(SHARE_CTRL_HDR_FMT, seq, ts_ms, PDU_TYPE_CONTROL, 0)
        msg_len = struct.pack(">I", len(message_bytes))
        return header + msg_len + message_bytes
    
    @staticmethod
    def build_input_pdu(seq, event_bytes):
        ts_ms = int(time.time() * 1000)
        header = struct.pack(SHARE_CTRL_HDR_FMT, seq, ts_ms, PDU_TYPE_INPUT, 0)
        msg_len = struct.pack(">I", len(event_bytes))
        return header + msg_len + event_bytes
