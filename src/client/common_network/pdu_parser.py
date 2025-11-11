# common_network/pdu_parser.py

import struct
import json
from .constants import (
    PDU_TYPE_FULL, PDU_TYPE_RECT, PDU_TYPE_CONTROL, PDU_TYPE_INPUT,
    SHARE_CTRL_HDR_FMT
)
from .mcs_layer import MCSLite

# Lớp giải mã gói PDU được truyền qua mạng
class PDUParser:
    def __init__(self):
        self.mcs = MCSLite()

    def parse(self, data: bytes):
        min_hdr = struct.calcsize(SHARE_CTRL_HDR_FMT)
        if len(data) < min_hdr:
            raise ValueError("PDU too small")
        seq, ts_ms, ptype, flags = struct.unpack(SHARE_CTRL_HDR_FMT, data[:min_hdr])
        offset = min_hdr
        base = {
            "seq": seq,
            "ts_ms": ts_ms,
            "flags": flags,
        }
        # giải mã ảnh toàn bộ màn hình 
        if ptype == PDU_TYPE_FULL:
            if len(data) < offset + 12:
                raise ValueError("FULL too small")
            width, height, jpg_len = struct.unpack(">III", data[offset:offset+12])
            offset += 12
            jpg = data[offset:offset+jpg_len]
            extra = {
                "type": "full",
                "width": width,
                "height": height,
                "jpg": jpg
            }
            return {**base, **extra}
        # giải mã ảnh vùng thay đổi 
        elif ptype == PDU_TYPE_RECT:
            if len(data) < offset + 20:
                raise ValueError("RECT too small")
            x, y, w, h, jpg_len = struct.unpack(">IIIII", data[offset:offset+20])
            offset += 20
            full_w, full_h = struct.unpack(">II", data[offset:offset+8])
            offset += 8
            jpg = data[offset:offset+jpg_len]
            extra = {
                "type": "rect",
                "x": x, "y": y, "w": w, "h": h,
                "full_w": full_w, "full_h": full_h,
                "jpg": jpg
            }
            return {**base, **extra}
        # giải mã thông báo điều khiển
        elif ptype == PDU_TYPE_CONTROL:
            if len(data) < offset + 4:
                raise ValueError("CONTROL too small")
            (msg_len,) = struct.unpack(">I", data[offset:offset+4])
            offset += 4
            msg = data[offset:offset+msg_len]
            try:
                msg_text = msg.decode(errors="ignore")
            except Exception:
                msg_text = ""
            extra = {
                "type": "control",
                "message": msg_text,
                "raw_message": msg
            }
            return {**base, **extra}
        # giải mã JSON chứa sự kiện chuột, bàn phím 
        elif ptype == PDU_TYPE_INPUT:
            if len(data) < offset + 4:
                raise ValueError("INPUT too small")
            (msg_len,) = struct.unpack(">I", data[offset:offset+4])
            offset += 4
            body = data[offset:offset+msg_len]
            try:
                obj = json.loads(body.decode())
            except Exception:
                obj = None
            extra = {
                "type": "input",
                "input": obj,
                "raw_body": body
            }
            return {**base, **extra}
        else:
            extra = {
                "type": "unknown",
                "ptype": ptype
            }
            return {**base, **extra}
    
    def parse_with_mcs(self, data: bytes, decrypt_fn=None):
        if decrypt_fn is not None:
            try:
                data = decrypt_fn(data)
            except Exception as e:
                raise ValueError(f"Decryption failed: {e}")

        # giải nén lớp MCS (2-byte channel id)
        ch_id, pdu_payload = self.mcs.unpack(data)
        ch_name = self.mcs.get_channel_name(ch_id)

        # phân tích tải trọng PDU
        parsed = self.parse(pdu_payload)

        # đính kèm thông tin kênh 
        parsed["channel_id"] = ch_id
        parsed["channel"] = ch_name
        return parsed
