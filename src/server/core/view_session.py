# server/core/view_session.py

import threading
from queue import Queue, Empty
from src.server.server_constants import CHANNEL_VIDEO, CHANNEL_CURSOR
from src.common.network.mcs_layer import MCSLite

class ViewSession:
    """
    View Session: Cho phép nhiều Manager xem màn hình của 1 Client
    - Client gửi video/cursor tới TẤT CẢ viewers
    - Không có input control
    - Nhiều manager có thể view cùng lúc (1-nhiều)
    - Client capture màn hình mỗi 2 giây để server lưu screenshot thường xuyên
    """
    def __init__(self, client_id, broadcaster):
        self.client_id = client_id
        self.broadcaster = broadcaster
        self.viewers = set()  # Set of manager_ids đang view
        self.lock = threading.Lock()
        self.running = True
        
        print(f"[ViewSession] Created for client {client_id}")
    
    def add_viewer(self, manager_id):
        """Thêm manager vào danh sách viewers"""
        with self.lock:
            if manager_id not in self.viewers:
                self.viewers.add(manager_id)
                print(f"[ViewSession] Manager {manager_id} joined viewing {self.client_id}. Total viewers: {len(self.viewers)}")
                return True
            return False
    
    def remove_viewer(self, manager_id):
        """Xóa manager khỏi danh sách viewers"""
        with self.lock:
            if manager_id in self.viewers:
                self.viewers.discard(manager_id)
                print(f"[ViewSession] Manager {manager_id} stopped viewing {self.client_id}. Remaining viewers: {len(self.viewers)}")
                return len(self.viewers) == 0  # Return True nếu không còn viewer nào
            return False
    
    def is_viewing(self, manager_id):
        """Kiểm tra xem manager có đang view không"""
        with self.lock:
            return manager_id in self.viewers
    
    def has_viewers(self):
        """Kiểm tra xem có viewer nào không"""
        with self.lock:
            return len(self.viewers) > 0
    
    def broadcast_frame(self, pdu_type, raw_payload):
        """
        Broadcast video/cursor frame tới tất cả viewers
        pdu_type: "full", "rect", "cursor"
        raw_payload: PDU bytes đã build
        """
        with self.lock:
            viewer_list = list(self.viewers)  # Copy để tránh modification during iteration
        
        if not viewer_list:
            return
        
        # Chọn channel dựa trên pdu_type
        if pdu_type in ("full", "rect"):
            channel_id = CHANNEL_VIDEO
        elif pdu_type == "cursor":
            channel_id = CHANNEL_CURSOR
        else:
            return
        
        # Build MCS frame một lần
        mcs_frame = MCSLite.build(channel_id, raw_payload)
        
        # Gửi tới tất cả viewers
        for manager_id in viewer_list:
            try:
                self.broadcaster.enqueue(manager_id, mcs_frame)
            except Exception as e:
                print(f"[ViewSession] Error broadcasting to {manager_id}: {e}")
    
    def get_viewer_count(self):
        """Lấy số lượng viewers"""
        with self.lock:
            return len(self.viewers)
    
    def stop(self):
        """Dừng view session"""
        self.running = False
        with self.lock:
            self.viewers.clear()
        print(f"[ViewSession] Stopped for client {self.client_id}")
