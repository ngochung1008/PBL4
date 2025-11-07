# common_network/pdu_parser.py
import struct
import json
from common_network.pdu_builder import PDU_TYPE_FULL, PDU_TYPE_RECT, PDU_TYPE_CONTROL, PDU_TYPE_INPUT, SHARE_CTRL_HDR_FMT

class PDUParser:
    def parse(self, data: bytes):
        min_hdr = struct.calcsize(SHARE_CTRL_HDR_FMT)
        if len(data) < min_hdr:
            raise ValueError("PDU too small")
        seq, ts_ms, ptype, flags = struct.unpack(SHARE_CTRL_HDR_FMT, data[:min_hdr])
        offset = min_hdr
        if ptype == PDU_TYPE_FULL:
            if len(data) < offset + 12:
                raise ValueError("FULL too small")
            width, height, jpg_len = struct.unpack(">III", data[offset:offset+12])
            offset += 12
            jpg = data[offset:offset+jpg_len]
            return {"type":"full","seq":seq,"ts_ms":ts_ms,"width":width,"height":height,"jpg":jpg}
        elif ptype == PDU_TYPE_RECT:
            if len(data) < offset + 20:
                raise ValueError("RECT too small")
            x, y, w, h, jpg_len = struct.unpack(">IIIII", data[offset:offset+20])
            offset += 20
            full_w, full_h = struct.unpack(">II", data[offset:offset+8])
            offset += 8
            jpg = data[offset:offset+jpg_len]
            return {"type":"rect","seq":seq,"ts_ms":ts_ms,"x":x,"y":y,"w":w,"h":h,"full_w":full_w,"full_h":full_h,"jpg":jpg}
        elif ptype == PDU_TYPE_CONTROL:
            if len(data) < offset + 4:
                raise ValueError("CONTROL too small")
            (msg_len,) = struct.unpack(">I", data[offset:offset+4])
            offset += 4
            msg = data[offset:offset+msg_len]
            return {"type":"control","seq":seq,"ts_ms":ts_ms,"message":msg.decode(errors="ignore")}
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
            return {"type":"input","seq":seq,"ts_ms":ts_ms,"input":obj}
        else:
            return {"type":"unknown","seq":seq,"ts_ms":ts_ms,"ptype":ptype}
