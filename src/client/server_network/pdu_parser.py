# File: server_network/pdu_parser.py
import struct

SHARE_CTRL_HDR_FMT = ">IQBB"

class PDUParser:
    def parse_pdu(self, data: bytes):
        # data here is the TPKT body (after the 4-byte header)
        if len(data) < struct.calcsize(SHARE_CTRL_HDR_FMT):
            raise ValueError("PDU too small")
        seq, ts_ms, ptype, flags = struct.unpack(SHARE_CTRL_HDR_FMT, data[:struct.calcsize(SHARE_CTRL_HDR_FMT)])
        offset = struct.calcsize(SHARE_CTRL_HDR_FMT)
        if ptype == 1:  # FULL
            if len(data) < offset + 12:
                raise ValueError("FULL frame too small")
            width, height, jpg_len = struct.unpack(">III", data[offset:offset+12])
            offset += 12
            jpg = data[offset:offset+jpg_len]
            return {"type": "full", "seq": seq, "ts_ms": ts_ms, "width": width, "height": height, "jpg_len": jpg_len, "jpg": jpg}
        elif ptype == 2:  # RECT
            if len(data) < offset + 20:
                raise ValueError("RECT frame too small")
            x, y, w, h, jpg_len = struct.unpack(">IIIII", data[offset:offset+20])
            offset += 20
            full_w, full_h = struct.unpack(">II", data[offset:offset+8])
            offset += 8
            jpg = data[offset:offset+jpg_len]
            return {"type": "rect", "seq": seq, "ts_ms": ts_ms, "x": x, "y": y, "w": w, "h": h, "full_w": full_w, "full_h": full_h, "jpg_len": jpg_len, "jpg": jpg}
        elif ptype == 3:  # CONTROL
            if len(data) < offset + 4:
                raise ValueError("CONTROL too small")
            (msg_len,) = struct.unpack(">I", data[offset:offset+4])
            offset += 4
            msg = data[offset:offset+msg_len]
            return {"type": "control", "seq": seq, "ts_ms": ts_ms, "message": msg.decode(errors='ignore')}
        else:
            return {"type": "unknown", "seq": seq, "ts_ms": ts_ms, "ptype": ptype}