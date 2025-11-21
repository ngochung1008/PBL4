# manager/manager_network/manager_receiver.py

import threading
import struct
import ssl
from collections import defaultdict
from common_network.mcs_layer import MCSLite
from common_network.pdu_parser import PDUParser
from common_network.tpkt_layer import TPKTLayer
from common_network.constants import (
    SHARE_CTRL_HDR_FMT, SHARE_HDR_SIZE,
    FRAGMENT_FLAG, FRAGMENT_HDR_FMT, FRAGMENT_HDR_SIZE,
    PDU_TYPE_FULL, PDU_TYPE_RECT, PDU_TYPE_CONTROL, PDU_TYPE_INPUT, PDU_TYPE_CURSOR,
    PDU_TYPE_FILE_START, PDU_TYPE_FILE_CHUNK, PDU_TYPE_FILE_END, 
    PDU_TYPE_FILE_ACK, PDU_TYPE_FILE_NAK
)
from manager.manager_constants import ALL_CHANNELS

class ManagerReceiver(threading.Thread):
    """
    Giống hệt ServerReceiver.
    Đọc TPKT từ SSL socket -> feed vào MCS -> xử lý buffer từng kênh
    -> trích xuất PDU -> đẩy PDU (dict) vào pdu_queue.
    """
    def __init__(self, ssl_sock, pdu_queue, done_callback):
        super().__init__(daemon=True, name="ManagerReceiver")
        self.sock = ssl_sock
        self.client_id = "server" # Chỉ có 1 kết nối tới server
        self.pdu_queue = pdu_queue
        self.done_callback = done_callback
        
        self.mcs = MCSLite()
        self.parser = PDUParser()
        self.running = True
        self.channel_buffers = defaultdict(bytearray)

    def _get_pdu_total_length(self, data: bytes) -> int:
        """
        Kiểm tra buffer và trả về tổng độ dài của PDU đầu tiên.
        (Logic giống hệt ServerReceiver)
        """
        if len(data) < SHARE_HDR_SIZE:
            raise ValueError("Không đủ dữ liệu cho header chung")
        
        seq, ts_ms, ptype, flags = struct.unpack_from(SHARE_CTRL_HDR_FMT, data)
        offset = SHARE_HDR_SIZE

        if (flags & FRAGMENT_FLAG):
            # Giả định 1 TPKT/MCS chỉ chứa 1 fragment PDU
            return len(data)

        try:
            if ptype == PDU_TYPE_FULL:
                if len(data) < offset + 12: raise ValueError("Thiếu header FULL")
                jpg_len = struct.unpack_from(">I", data, offset + 8)[0]
                return offset + 12 + jpg_len
            
            elif ptype == PDU_TYPE_RECT:
                if len(data) < offset + 28: raise ValueError("Thiếu header RECT")
                jpg_len = struct.unpack_from(">I", data, offset + 16)[0]
                return offset + 28 + jpg_len
            
            elif ptype == PDU_TYPE_CONTROL or ptype == PDU_TYPE_INPUT:
                if len(data) < offset + 4: raise ValueError("Thiếu header CONTROL/INPUT")
                msg_len = struct.unpack_from(">I", data, offset)[0]
                return offset + 4 + msg_len
            
            elif ptype == PDU_TYPE_CURSOR:
                if len(data) < offset + 12: raise ValueError("Thiếu header CURSOR")
                shape_len = struct.unpack_from(">I", data, offset + 8)[0]
                return offset + 12 + shape_len
                
            elif ptype == PDU_TYPE_FILE_START:
                if len(data) < offset + 2: raise ValueError("Thiếu header FILE_START")
                fn_len = struct.unpack_from(">H", data, offset)[0]
                return offset + 2 + fn_len + 16
                
            elif ptype == PDU_TYPE_FILE_CHUNK:
                if len(data) < offset + 12: raise ValueError("Thiếu header FILE_CHUNK")
                chunk_len = struct.unpack_from(">I", data, offset + 8)[0]
                return offset + 12 + chunk_len
                
            elif ptype == PDU_TYPE_FILE_END:
                return offset + 4
                
            elif ptype == PDU_TYPE_FILE_ACK:
                return offset + 8
                
            elif ptype == PDU_TYPE_FILE_NAK:
                if len(data) < offset + 12: raise ValueError("Thiếu header FILE_NAK")
                reason_len = struct.unpack_from(">I", data, offset + 8)[0]
                return offset + 12 + reason_len
                
            else:
                raise ValueError(f"Loại PDU không xác định: {ptype}")
                
        except struct.error:
            raise ValueError("Không đủ dữ liệu để đọc độ dài PDU")

    def _process_channel_buffer(self, channel_id: int):
        """
        Xử lý buffer cho một kênh, trích xuất các PDU hoàn chỉnh.
        """
        buf = self.channel_buffers[channel_id]
        
        while self.running:
            if not buf:
                break

            try:
                total_pdu_len = self._get_pdu_total_length(bytes(buf))
            except ValueError:
                break 

            if len(buf) < total_pdu_len:
                break
                
            pdu_bytes = buf[:total_pdu_len]
            del buf[:total_pdu_len]

            try:
                parsed = self.parser.parse(pdu_bytes)
            except Exception as e:
                print(f"[ManagerReceiver] Lỗi parse PDU, bỏ qua: {e}")
                continue

            if parsed and parsed.get("type") != "fragment_pending":
                if parsed.get("type") in ("control", "cursor", "input"):
                    print(f"[ManagerReceiver] NHẬN GÓI TIN NHỎ: {parsed.get('type')} Channel: {channel_id}")
                parsed["_raw_payload"] = pdu_bytes
                
                # Đẩy PDU (dict) vào hàng đợi chung
                self.pdu_queue.put(parsed)

    def run(self):
        try:
            while self.running:
                try:
                    tpkt_body = TPKTLayer.recv_one(self.sock, recv_fn=self.sock.recv, timeout=600.0)
                except (TimeoutError, ConnectionError, OSError, ssl.SSLError) as e:
                    if self.running:
                        print(f"[ManagerReceiver] Mất kết nối tới Server: {e}")
                    break

                if not tpkt_body:
                    if self.running: print(f"[ManagerReceiver] Nhận 0 bytes, kết thúc.")
                    break
                    
                self.mcs.feed(tpkt_body)

                for ch_id in ALL_CHANNELS:
                    new_data = self.mcs.read_channel(ch_id)
                    if new_data:
                        self.channel_buffers[ch_id].extend(new_data)
                    
                    self._process_channel_buffer(ch_id)

        except Exception as e:
            if self.running:
                print(f"[ManagerReceiver] Lỗi nghiêm trọng: {e}")
        finally:
            self.running = False
            try: self.sock.shutdown(2)
            except: pass
            try: self.sock.close()
            except: pass
            if self.done_callback:
                self.done_callback()
            print("[ManagerReceiver] Đã dừng.")

    def stop(self):
        self.running = False
        try:
            self.sock.shutdown(2)
        except Exception:
            pass