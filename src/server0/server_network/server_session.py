# server0/server_network/server_session.py

import threading
from queue import Queue, Empty
from server0.server_constants import (
    CHANNEL_VIDEO, CHANNEL_CONTROL, CHANNEL_INPUT, CHANNEL_FILE, CHANNEL_CURSOR,
    CMD_DISCONNECT
)
from common_network.mcs_layer import MCSLite

class ServerSession(threading.Thread):
    """
    Một luồng (thread) chuyên dụng để xử lý logic
    cho 1 Manager và 1 Client ĐÃ KẾT NỐI VỚI NHAU.
    """
    def __init__(self, manager_id, client_id, broadcaster, done_callback):
        self.session_id = f"{manager_id}::{client_id}"
        super().__init__(daemon=True, name=f"Session-{self.session_id}")
        
        self.manager_id = manager_id
        self.client_id = client_id
        self.broadcaster = broadcaster
        self.done_callback = done_callback # Báo cho SessionManager khi kết thúc
        
        self.pdu_queue = Queue(maxsize=4096) # Queue riêng của phiên này
        self.running = True

    def enqueue_pdu(self, from_id, pdu):
        """SessionManager gọi hàm này để đưa PDU vào xử lý"""
        if not self.running:
            return
            
        # 1. Nếu PDU mới là Video/Cursor và queue đầy -> HỦY BỎ PDU MỚI (ít quan trọng hơn)
        if pdu.get("type") in ("full", "rect") and self.pdu_queue.full(): 
            return # Bỏ PDU mới

        try:
            self.pdu_queue.put((from_id, pdu), block=False)
        except Queue.Full:
            # 2. Nếu PDU mới là Control/Input/File (quan trọng) và queue vẫn đầy,
            #  => bỏ PDU cũ nhất (có khả năng là Video/Cursor) để chèn PDU mới
            if pdu.get("type") not in ("full", "rect"):
                try: 
                    # Loại bỏ 1 phần tử cũ nhất
                    self.pdu_queue.get_nowait()
                    # Chèn PDU quan trọng mới
                    self.pdu_queue.put((from_id, pdu), block=False)
                except: 
                    # Nếu vẫn không thể chèn (rất hiếm), bỏ qua
                    pass
            
    def run(self):
        print(f"[ServerSession-{self.session_id}] Đã khởi động.")
        reason = "Unknown"
        
        try:
            while self.running:
                try:
                    from_id, pdu = self.pdu_queue.get(timeout=0.5)
                except Empty:
                    continue
                
                # --- Quy tắc chuyển tiếp (Routing) ---
                
                ptype = pdu.get("type")
                raw_payload = pdu.get("_raw_payload")
                
                if not raw_payload:
                    continue

                if from_id == self.client_id:
                    # --- Từ Client -> Gửi cho Manager ---
                    target_id = self.manager_id
                    
                    if ptype in ("full", "rect"):
                        # (Video) Gửi trên kênh VIDEO
                        mcs_frame = MCSLite.build(CHANNEL_VIDEO, raw_payload)
                    elif ptype == "cursor":
                        # (Cursor) Gửi trên kênh CURSOR
                        mcs_frame = MCSLite.build(CHANNEL_CURSOR, raw_payload)
                    elif ptype == "control":
                        # (Control) Gửi trên kênh CONTROL
                        if pdu.get("message") == CMD_DISCONNECT:
                            reason = f"Client {self.client_id} yêu cầu ngắt kết nối."
                            self.running = False
                        mcs_frame = MCSLite.build(CHANNEL_CONTROL, raw_payload)
                    elif ptype == "input":
                        # (Input - ví dụ: keylogger) Gửi trên kênh INPUT
                        mcs_frame = MCSLite.build(CHANNEL_INPUT, raw_payload)
                    else:
                        # (File) Gửi trên kênh FILE
                        mcs_frame = MCSLite.build(CHANNEL_FILE, raw_payload)
                        
                    self.broadcaster.enqueue(target_id, mcs_frame)
                    
                elif from_id == self.manager_id:
                    # --- Từ Manager -> Gửi cho Client ---
                    target_id = self.client_id
                    
                    if ptype == "input":
                        # (Input) Gửi trên kênh INPUT
                        mcs_frame = MCSLite.build(CHANNEL_INPUT, raw_payload)
                    elif ptype == "control":
                        # (Control) Gửi trên kênh CONTROL
                        if pdu.get("message") == CMD_DISCONNECT:
                            reason = f"Manager {self.manager_id} yêu cầu ngắt kết nối."
                            self.running = False
                        mcs_frame = MCSLite.build(CHANNEL_CONTROL, raw_payload)
                    elif ptype != "full" and ptype != "rect" and ptype != "cursor":
                        # (File) và các PDU khác không phải video/cursor
                         mcs_frame = MCSLite.build(CHANNEL_FILE, raw_payload)
                    else:
                        continue
                    
                    self.broadcaster.enqueue(target_id, mcs_frame)
                    
                if not self.running:
                    break # Thoát vòng lặp
                    
        except Exception as e:
            reason = f"Lỗi nghiêm trọng: {e}"
            print(f"[ServerSession-{self.session_id}] Lỗi: {e}")
        finally:
            self.running = False
            self.done_callback(self, reason)
            print(f"[ServerSession-{self.session_id}] Đã dừng. Lý do: {reason}")

    def stop(self):
        self.running = False
        with self.pdu_queue.mutex:
            self.pdu_queue.queue.clear()