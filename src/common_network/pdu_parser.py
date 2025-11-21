# common_network/pdu_parser.py

import json
import struct
import time
from typing import Optional, Dict,  Tuple
from common_network.constants import (
    PDU_TYPE_CURSOR, PDU_TYPE_FULL, PDU_TYPE_RECT, PDU_TYPE_CONTROL, PDU_TYPE_INPUT,
    PDU_TYPE_FILE_START, PDU_TYPE_FILE_CHUNK, PDU_TYPE_FILE_END, PDU_TYPE_FILE_ACK, PDU_TYPE_FILE_NAK,
    SHARE_CTRL_HDR_FMT, SHARE_HDR_SIZE,
    FRAGMENT_FLAG, FRAGMENT_HDR_FMT, FRAGMENT_HDR_SIZE,
    FRAGMENT_ASSEMBLY_TIMEOUT, MAX_FRAGMENTS_PER_SEQ, MAX_BUFFERED_BYTES_PER_SEQ
)

class PDUParser:
    def __init__(self):
        self.fragment_buffer: Dict[int, Dict] = {} # [seq, dict ["total", "parts" (offset->bytes), "ptype", "ts_ms", "first_ts"]]

    # Kiểm tra xem PDU có phải là fragment không
    def _is_fragment(self, flags: int) -> bool:
        return (flags & FRAGMENT_FLAG) != 0

    # Dọn dẹp các fragment cũ đã hết hạn
    def _cleanup_old_fragments(self) -> None:
        now = time.time()
        to_delete = []
        for seq, meta in list(self.fragment_buffer.items()):
            first_ts = meta.get("first_ts", now)
            if now - first_ts > FRAGMENT_ASSEMBLY_TIMEOUT:
                to_delete.append(seq)
        for seq in to_delete:
            try:
                del self.fragment_buffer[seq]
            except KeyError:
                pass

    # Lưu fragment và kiểm tra xem có thể lắp ráp PDU hoàn chỉnh không
    def _store_fragment(self, seq: int, ts_ms: int, ptype: int, frag_offset: int, total_len: int, payload: bytes) -> Optional[bytes]:
        self._cleanup_old_fragments()

        meta = self.fragment_buffer.get(seq)
        if meta is None:
            meta = {
                "total": total_len,
                "parts": {},
                "ptype": ptype,
                "ts_ms": ts_ms,
                "first_ts": time.time(),
            }
            self.fragment_buffer[seq] = meta

        if total_len != meta["total"]:
            try:
                del self.fragment_buffer[seq]
            except KeyError:
                pass
            raise ValueError("fragment total_len conflicted")

        if len(meta["parts"]) >= MAX_FRAGMENTS_PER_SEQ:
            del self.fragment_buffer[seq]
            raise MemoryError("too many fragments for seq")

        current_buffered = sum(len(b) for b in meta["parts"].values())
        if current_buffered + len(payload) > MAX_BUFFERED_BYTES_PER_SEQ:
            del self.fragment_buffer[seq]
            raise MemoryError("fragment assembly would exceed MAX_BUFFERED_BYTES_PER_SEQ")

        meta["parts"][frag_offset] = payload

        received = sum(len(b) for b in meta["parts"].values())
        if received >= meta["total"]:
            parts = meta["parts"]
            assembled = bytearray()
            for off in sorted(parts.keys()):
                assembled.extend(parts[off])
            try:
                del self.fragment_buffer[seq]
            except KeyError:
                pass
            
            # header PDU đã lắp ráp
            flags = 0 # xóa cờ fragment
            header = struct.pack(SHARE_CTRL_HDR_FMT, seq, meta["ts_ms"], meta["ptype"], flags)
            
            return header + assembled
        
        return None

    def parse(self, data: bytes, reassemble: bool = True) -> Optional[dict]:
        """
        Phân tích (parse) MỘT PDU payload (frame) duy nhất
        1. Phân tích PDU.
        2. Nếu là fragment, lưu nó lại và trả về None (hoặc "pending").
        3. Nếu là fragment cuối cùng, lắp ráp và trả về PDU HOÀN CHỈNH.
        4. Nếu là PDU thường, phân tích và trả về dict.
        """
        if len(data) < SHARE_HDR_SIZE:
            raise ValueError("PDU too small")

        seq, ts_ms, ptype, flags = struct.unpack(SHARE_CTRL_HDR_FMT, data[:SHARE_HDR_SIZE])
        offset = SHARE_HDR_SIZE

        if self._is_fragment(flags):
            if not reassemble:
                base = {"seq": seq, "ts_ms": ts_ms, "flags": flags}
                # Trả về đúng loại PDU để ServerSession biết đường routing
                if ptype == PDU_TYPE_FULL: return {**base, "type": "full"}
                if ptype == PDU_TYPE_RECT: return {**base, "type": "rect"}
                if ptype == PDU_TYPE_CURSOR: return {**base, "type": "cursor"}
                return {**base, "type": "unknown_fragment"}
            
            if len(data) < SHARE_HDR_SIZE + FRAGMENT_HDR_SIZE:
                raise ValueError("fragment PDU too small for frag header")
            
            frag_offset, total_len = struct.unpack(FRAGMENT_HDR_FMT, data[offset:offset+FRAGMENT_HDR_SIZE])
            offset += FRAGMENT_HDR_SIZE 
            frag_payload = data[offset:] # phần dữ liệu fragment
            assembled_pdu_bytes = self._store_fragment(seq, ts_ms, ptype, frag_offset, total_len, frag_payload) # lưu fragment
            
            # nếu chưa đủ, _store_fragment trả về None. Hàm parse trả về PDU "đặc biệt"
            if assembled_pdu_bytes is None:
                # Vẫn đang chờ, trả về một PDU "đặc biệt"
                return {"seq": seq, "ts_ms": ts_ms, "type": "fragment_pending"}
            # nếu đã đủ, _strore_fragment sẽ lắp ráp tất cả các mẫu, tạo và trả về PDU gốc hoàn chỉnh
            data = assembled_pdu_bytes 
            
            # phân tích lại PDU hoàn chỉnh (lấy header mới)
            seq, ts_ms, ptype, flags = struct.unpack(SHARE_CTRL_HDR_FMT, data[:SHARE_HDR_SIZE])
            offset = SHARE_HDR_SIZE
            # cờ fragment bây giờ đã là 0

        # Nếu PDU là fragment, code sẽ chạy đến đây sau khi lắp ráp xong
        base = {"seq": seq, "ts_ms": ts_ms, "flags": flags}

        if ptype == PDU_TYPE_FULL:
            if len(data) < offset + 12:
                raise ValueError("FULL too small")
            width, height, jpg_len = struct.unpack(">III", data[offset:offset+12])
            offset += 12
            if offset + jpg_len > len(data):
                raise ValueError("FULL jpg length exceeds payload")
            jpg = data[offset:offset+jpg_len]
            return {**base, "type": "full", "width": width, "height": height, "jpg": jpg}

        elif ptype == PDU_TYPE_RECT:
            if len(data) < offset + 20:
                raise ValueError("RECT too small")
            x, y, w, h, jpg_len = struct.unpack(">IIIII", data[offset:offset+20])
            offset += 20
            if offset + 8 > len(data):
                raise ValueError("RECT missing full dims")
            full_w, full_h = struct.unpack(">II", data[offset:offset+8])
            offset += 8
            if offset + jpg_len > len(data):
                raise ValueError("RECT jpg length exceeds payload")
            jpg = data[offset:offset+jpg_len]
            return {
                **base, "type": "rect", "x": x, "y": y, "w": w, "h": h,
                "full_w": full_w, "full_h": full_h, "jpg": jpg
            }

        elif ptype == PDU_TYPE_CONTROL:
            if len(data) < offset + 4:
                raise ValueError("CONTROL missing length")
            (msg_len,) = struct.unpack(">I", data[offset:offset+4])
            offset += 4
            if offset + msg_len > len(data):
                raise ValueError("CONTROL msg exceeds payload")
            msg = data[offset:offset+msg_len]
            return {**base, "type": "control", "message": msg.decode(errors="ignore"), "raw_message": msg}

        elif ptype == PDU_TYPE_INPUT:
            if len(data) < offset + 4:
                raise ValueError("INPUT missing length")
            (msg_len,) = struct.unpack(">I", data[offset:offset+4])
            offset += 4
            if offset + msg_len > len(data):
                raise ValueError("INPUT body exceeds payload")
            body = data[offset:offset+msg_len]
            obj = None
            try:
                obj = json.loads(body.decode())
            except Exception:
                pass
            return {**base, "type": "input", "input": obj, "raw_body": body}

        elif ptype == PDU_TYPE_CURSOR:
            if len(data) < offset + 12:
                raise ValueError("CURSOR too small")
            x, y, shape_len = struct.unpack(">III", data[offset:offset+12])
            offset += 12
            
            cursor_shape = data[offset:offset+shape_len]
            
            return {
                **base, "type": "cursor", "x": x, "y": y, 
                "cursor_shape": cursor_shape
            }

        elif ptype == PDU_TYPE_FILE_START:
            if len(data) < offset + 2:
                raise ValueError("FILE_START too small")
            fn_len, = struct.unpack(">H", data[offset:offset+2])
            offset += 2
            if offset + fn_len + 16 > len(data):
                raise ValueError("FILE_START missing fields")
            filename = data[offset:offset+fn_len].decode(errors="ignore")
            offset += fn_len
            total_size, chunk_size, checksum = struct.unpack(">Q I I", data[offset:offset+16])
            return {
                **base, "type": "file_start", "filename": filename,
                "total_size": total_size, "chunk_size": chunk_size, "checksum": checksum
            }
        
        elif ptype == PDU_TYPE_FILE_CHUNK:
            if len(data) < offset + 12:
                raise ValueError("FILE_CHUNK too small")
            frag_offset, chunk_len = struct.unpack(">Q I", data[offset:offset+12])
            offset += 12
            if offset + chunk_len > len(data):
                raise ValueError("FILE_CHUNK data exceeds payload")
            chunk_data = data[offset:offset+chunk_len]
            return {
                **base, "type": "file_chunk", "offset": frag_offset,
                "data": chunk_data
            }
        
        elif ptype == PDU_TYPE_FILE_END:
            if len(data) < offset + 4:
                raise ValueError("FILE_END too small")
            (checksum,) = struct.unpack(">I", data[offset:offset+4])
            return {**base, "type": "file_end", "checksum": checksum}
        
        elif ptype == PDU_TYPE_FILE_ACK:
            if len(data) < offset + 8:
                raise ValueError("FILE_ACK too small")
            (ack_offset,) = struct.unpack(">Q", data[offset:offset+8])
            return {**base, "type": "file_ack", "ack_offset": ack_offset}
        
        elif ptype == PDU_TYPE_FILE_NAK:
            if len(data) < offset + 12:
                raise ValueError("FILE_NAK too small")
            frag_offset, reason_len = struct.unpack(">Q I", data[offset:offset+12])
            offset += 12
            if offset + reason_len > len(data):
                raise ValueError("FILE_NAK reason exceeds payload")
            reason = data[offset:offset+reason_len]
            return {
                **base, "type": "file_nak", "offset": frag_offset,
                "reason": reason.decode(errors="ignore"), "raw_reason": reason
            }

        return {**base, "type": "unknown", "ptype": ptype}
