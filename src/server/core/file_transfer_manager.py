"""
File Transfer Manager - Quản lý việc truyền file giữa manager và client
Lưu trữ lịch sử và xử lý logic transfer
"""

import os
import hashlib
import threading
import time
from datetime import datetime
from typing import Optional, Dict, Any
import mysql.connector
from config import server_config

class FileTransferManager:
    """Quản lý file transfer và lưu lịch sử vào database"""
    
    def __init__(self):
        self.db_lock = threading.Lock()
        self.active_transfers = {}  # {transfer_id: transfer_info}
        self.temp_file_storage = {}  # {transfer_id: file_chunks}
        
    def _get_db_connection(self):
        """Tạo kết nối database"""
        try:
            return mysql.connector.connect(
                host=server_config.host_db,
                user=server_config.user_db,
                password=server_config.password_db,
                database=server_config.database_db
            )
        except Exception as e:
            print(f"[FileTransferManager] Database connection error: {e}")
            return None
    
    def create_transfer_record(self, sender_id: str, sender_type: str, 
                              receiver_id: str, receiver_type: str,
                              filename: str, filesize: int,
                              file_hash: Optional[str] = None) -> Optional[int]:
        """
        Tạo bản ghi transfer mới - không lưu database, chỉ tạo ID tạm
        Returns: transfer_id (timestamp-based)
        """
        import time
        
        # Tạo transfer_id từ timestamp (không cần database)
        transfer_id = int(time.time() * 1000) % 1000000  # 6 digits
        
        # Lưu vào memory thay vì database
        self.active_transfers[transfer_id] = {
            'sender_id': sender_id,
            'sender_type': sender_type,
            'receiver_id': receiver_id,
            'receiver_type': receiver_type,
            'filename': filename,
            'filesize': filesize,
            'file_hash': file_hash,
            'status': 'sending',
            'started_at': datetime.now()
        }
        
        print(f"[FileTransferManager] Created transfer #{transfer_id} (in-memory): "
              f"{sender_id}({sender_type}) -> {receiver_id}({receiver_type}): {filename}")
        
        return transfer_id
    
    def update_transfer_status(self, transfer_id: int, status: str, 
                              error_message: Optional[str] = None):
        """Cập nhật trạng thái transfer - chỉ in-memory, không database"""
        if transfer_id in self.active_transfers:
            self.active_transfers[transfer_id]['status'] = status
            if error_message:
                self.active_transfers[transfer_id]['error_message'] = error_message
            if status in ('completed', 'failed'):
                self.active_transfers[transfer_id]['completed_at'] = datetime.now()
            print(f"[FileTransferManager] Updated transfer #{transfer_id} status: {status}")
        else:
            print(f"[FileTransferManager] Transfer #{transfer_id} not found in memory")
    
    def get_transfer_history(self, entity_id: str, entity_type: str, 
                           limit: int = 50) -> list:
        """
        Lấy lịch sử transfer từ memory (không dùng database)
        """
        results = []
        for tid, info in self.active_transfers.items():
            if (info.get('sender_id') == entity_id and info.get('sender_type') == entity_type) or \
               (info.get('receiver_id') == entity_id and info.get('receiver_type') == entity_type):
                results.append({'id': tid, **info})
        return results[:limit]
    
    def get_all_transfers(self, limit: int = 100) -> list:
        """Lấy tất cả lịch sử transfer từ memory"""
        results = []
        for tid, info in self.active_transfers.items():
            results.append({'id': tid, **info})
        return results[:limit]
    
    def calculate_file_hash(self, file_data: bytes) -> str:
        """Tính SHA256 hash của file"""
        return hashlib.sha256(file_data).hexdigest()
    
    def validate_file_size(self, filesize: int) -> bool:
        """Kiểm tra file size có hợp lệ không"""
        max_size = getattr(server_config, 'max_file_size', 100 * 1024 * 1024)  # Default 100MB
        return 0 < filesize <= max_size
    
    def start_transfer(self, transfer_id: int, file_data: bytes):
        """Bắt đầu một transfer"""
        with self.db_lock:
            self.active_transfers[transfer_id] = {
                'data': file_data,
                'started_at': time.time()
            }
    
    def complete_transfer(self, transfer_id: int):
        """Hoàn thành transfer"""
        with self.db_lock:
            if transfer_id in self.active_transfers:
                del self.active_transfers[transfer_id]
        self.update_transfer_status(transfer_id, 'completed')
    
    def fail_transfer(self, transfer_id: int, error: str):
        """Đánh dấu transfer thất bại"""
        with self.db_lock:
            if transfer_id in self.active_transfers:
                del self.active_transfers[transfer_id]
        self.update_transfer_status(transfer_id, 'failed', error)
