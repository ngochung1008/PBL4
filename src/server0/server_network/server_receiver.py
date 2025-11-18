import ssl
import threading
import struct
from collections import defaultdict
from common_network.mcs_layer import MCSLite
from common_network.pdu_parser import PDUParser
from common_network.tpkt_layer import TPKTLayer
from common_network.constants import (
    SHARE_CTRL_HDR_FMT, SHARE_HDR_SIZE,
    FRAGMENT_FLAG, FRAGMENT_HDR_FMT, FRAGMENT_HDR_SIZE,
    PDU_TYPE_FULL, PDU_TYPE_RECT, PDU_TYPE_CONTROL, PDU_TYPE_INPUT,
    PDU_TYPE_FILE_START, PDU_TYPE_FILE_CHUNK, PDU_TYPE_FILE_END, 
    PDU_TYPE_FILE_ACK, PDU_TYPE_FILE_NAK
)
from server0.server_constants import ALL_CHANNELS

class ServerReceiver(threading.Thread):
    """
    Thread đọc TPKT từ SSL socket -> feed vào MCS.
    Sau đó, đọc từng channel, đưa vào buffer riêng của channel đó.
    Xử lý buffer để trích xuất từng PDU hoàn chỉnh.
    Đẩy PDU (dict) đã parse vào pdu_queue (hàng đợi chung của ServerNetwork).
    """
    def __init__(self, ssl_sock, client_id: str, pdu_queue, done_callback):
        super().__init__(daemon=True, name=f"Receiver-{client_id}")
        self.sock = ssl_sock
        self.client_id = client_id
        self.pdu_queue = pdu_queue
        self.done_callback = done_callback # Hàm gọi khi thread này kết thúc
        
        self.mcs = MCSLite()
        self.parser = PDUParser()
        self.running = True
        
        # Buffer đệm cho từng channel
        # { channel_id -> bytearray() }
        self.channel_buffers = defaultdict(bytearray)

    def _get_pdu_total_length(self, data: bytes) -> int:
        """
        Kiểm tra buffer và trả về tổng độ dài của PDU đầu tiên.
        Ném ValueError nếu không đủ dữ liệu để xác định độ dài.
        Đây là phần logic "mô phỏng" lại PDUParser để biết PDU dài bao nhiêu.
        """
        if len(data) < SHARE_HDR_SIZE:
            raise ValueError("Không đủ dữ liệu cho header chung")
        
        seq, ts_ms, ptype, flags = struct.unpack_from(SHARE_CTRL_HDR_FMT, data)
        offset = SHARE_HDR_SIZE

        # Xử lý PDU phân mảnh
        if (flags & FRAGMENT_FLAG):
            if len(data) < offset + FRAGMENT_HDR_SIZE:
                raise ValueError("Không đủ dữ liệu cho header phân mảnh")
            
            frag_offset, total_len = struct.unpack_from(FRAGMENT_HDR_FMT, data, offset)
            offset += FRAGMENT_HDR_SIZE
            
            # Với fragment, chúng ta không biết trước độ dài payload
            # Thay vì đoán, PDUParser.parse() sẽ trả về "fragment_pending"
            # Nhưng nó vẫn cần đọc hết payload. Làm sao biết payload dài bao nhiêu?
            # Đây là một điểm yếu trong thiết kế PDU: fragment không có length!
            # GIẢ ĐỊNH: Một TPKT/MCS chỉ chứa MỘT fragment.
            # => Toàn bộ phần còn lại của `data` là payload của fragment.
            # => _process_channel_buffer sẽ chỉ parse 1 PDU/lần.
            return len(data) # Giả định phần còn lại là payload

        # Xử lý PDU thường
        try:
            if ptype == PDU_TYPE_FULL:
                if len(data) < offset + 12: raise ValueError("Thiếu header FULL")
                jpg_len = struct.unpack_from(">I", data, offset + 8)[0]
                return offset + 12 + jpg_len
            
            elif ptype == PDU_TYPE_RECT:
                if len(data) < offset + 20: raise ValueError("Thiếu header RECT")
                jpg_len = struct.unpack_from(">I", data, offset + 16)[0]
                return offset + 20 + 8 + jpg_len # 8 = full_w, full_h
            
            elif ptype == PDU_TYPE_CONTROL or ptype == PDU_TYPE_INPUT:
                if len(data) < offset + 4: raise ValueError("Thiếu header CONTROL/INPUT")
                msg_len = struct.unpack_from(">I", data, offset)[0]
                return offset + 4 + msg_len
                
            elif ptype == PDU_TYPE_FILE_START:
                if len(data) < offset + 2: raise ValueError("Thiếu header FILE_START")
                fn_len = struct.unpack_from(">H", data, offset)[0]
                return offset + 2 + fn_len + 16 # 16 = QII (size, chunk, checksum)
                
            elif ptype == PDU_TYPE_FILE_CHUNK:
                if len(data) < offset + 12: raise ValueError("Thiếu header FILE_CHUNK")
                chunk_len = struct.unpack_from(">I", data, offset + 8)[0]
                return offset + 12 + chunk_len
                
            elif ptype == PDU_TYPE_FILE_END:
                return offset + 4 # I (checksum)
                
            elif ptype == PDU_TYPE_FILE_ACK:
                return offset + 8 # Q (ack_offset)
                
            elif ptype == PDU_TYPE_FILE_NAK:
                if len(data) < offset + 12: raise ValueError("Thiếu header FILE_NAK")
                reason_len = struct.unpack_from(">I", data, offset + 8)[0]
                return offset + 12 + reason_len
                
            else:
                # Loại PDU không xác định, không thể biết độ dài
                raise ValueError(f"Loại PDU không xác định: {ptype}")
                
        except struct.error:
            # Không đủ byte để unpack độ dài
            raise ValueError("Không đủ dữ liệu để đọc độ dài PDU")

    def _process_channel_buffer(self, channel_id: int):
        """
        Xử lý buffer cho một kênh cụ thể.
        Trích xuất và parse tất cả các PDU hoàn chỉnh trong buffer.
        """
        buf = self.channel_buffers[channel_id]
        
        while self.running:
            if not buf:
                break # Buffer rỗng

            try:
                # 1. Xác định độ dài PDU
                total_pdu_len = self._get_pdu_total_length(bytes(buf))
                
            except ValueError:
                # Không đủ dữ liệu để xác định độ dài PDU, chờ thêm
                break 

            # 2. Kiểm tra xem đã có đủ PDU hoàn chỉnh chưa
            if len(buf) < total_pdu_len:
                # Đã biết độ dài nhưng chưa nhận đủ, chờ thêm
                break
                
            # 3. Trích xuất PDU
            pdu_bytes = buf[:total_pdu_len]
            del buf[:total_pdu_len] # Tiêu thụ PDU khỏi buffer

            # 4. Parse PDU
            try:
                parsed = self.parser.parse(pdu_bytes)
            except Exception as e:
                print(f"[Receiver-{self.client_id}] Lỗi parse PDU, bỏ qua: {e}")
                continue # Bỏ qua PDU hỏng

            # 5. Đẩy PDU vào hàng đợi chung
            if parsed and parsed.get("type") != "fragment_pending":
                parsed["_raw_payload"] = pdu_bytes
                parsed["client_id"] = self.client_id
                
                # Đẩy (client_id, pdu_dict)
                self.pdu_queue.put((self.client_id, parsed))
                
            elif parsed and parsed.get("type") == "fragment_pending":
                # Vẫn đang chờ mảnh, không làm gì cả
                pass

    def run(self):
        try:
            while self.running:
                try:
                    # 1. Nhận một TPKT (bên trong là MCS)
                    # recv_fn=self.sock.recv sẽ đọc từ SSL socket
                    tpkt_body = TPKTLayer.recv_one(self.sock, recv_fn=self.sock.recv, timeout=600.0)
                    
                except (TimeoutError, ConnectionError, OSError, ssl.SSLError) as e:
                    if self.running:
                        print(f"[Receiver-{self.client_id}] Mất kết nối: {e}")
                    break # Kết thúc thread

                if not tpkt_body:
                    if self.running: print(f"[Receiver-{self.client_id}] Nhận 0 bytes, kết thúc.")
                    break
                    
                # 2. Feed TPKT body vào MCS layer
                self.mcs.feed(tpkt_body)

                # 3. Xử lý dữ liệu cho từng kênh
                for ch_id in ALL_CHANNELS:
                    # Lấy dữ liệu mới từ MCS (hàm này flush buffer của MCS)
                    new_data = self.mcs.read_channel(ch_id)
                    if new_data:
                        # Thêm vào buffer đệm của Receiver
                        self.channel_buffers[ch_id].extend(new_data)
                    
                    # Xử lý buffer đệm để trích xuất PDU
                    self._process_channel_buffer(ch_id)

        except Exception as e:
            if self.running:
                print(f"[Receiver-{self.client_id}] Lỗi nghiêm trọng: {e}")
        finally:
            # --- Dọn dẹp ---
            self.running = False
            try:
                self.sock.shutdown(2)
            except: pass
            try:
                self.sock.close()
            except: pass
            
            # Báo cho ServerNetwork biết thread này đã chết
            if self.done_callback:
                self.done_callback(self.client_id)
            print(f"[Receiver-{self.client_id}] Đã dừng.")

    def stop(self):
        self.running = False
        try:
            self.sock.shutdown(2)
        except Exception:
            pass