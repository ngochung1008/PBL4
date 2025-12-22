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
        Tạo bản ghi transfer mới trong database
        Returns: transfer_id nếu thành công, None nếu thất bại
        """
        conn = self._get_db_connection()
        if not conn:
            return None
            
        try:
            cursor = conn.cursor()
            sql = """
                INSERT INTO file_transfers 
                (sender_id, sender_type, receiver_id, receiver_type, 
                 filename, filesize, file_hash, status, transfer_started_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                sender_id, sender_type, receiver_id, receiver_type,
                filename, filesize, file_hash, 'sending', datetime.now()
            ))
            conn.commit()
            transfer_id = cursor.lastrowid
            
            print(f"[FileTransferManager] Created transfer record #{transfer_id}: "
                  f"{sender_id}({sender_type}) -> {receiver_id}({receiver_type}): {filename}")
            
            return transfer_id
        except Exception as e:
            print(f"[FileTransferManager] Error creating transfer record: {e}")
            return None
        finally:
            cursor.close()
            conn.close()
    
    def update_transfer_status(self, transfer_id: int, status: str, 
                              error_message: Optional[str] = None):
        """Cập nhật trạng thái transfer"""
        conn = self._get_db_connection()
        if not conn:
            return
            
        try:
            cursor = conn.cursor()
            
            if status == 'completed':
                sql = """
                    UPDATE file_transfers 
                    SET status = %s, transfer_completed_at = %s
                    WHERE id = %s
                """
                cursor.execute(sql, (status, datetime.now(), transfer_id))
            elif status == 'failed':
                sql = """
                    UPDATE file_transfers 
                    SET status = %s, error_message = %s, transfer_completed_at = %s
                    WHERE id = %s
                """
                cursor.execute(sql, (status, error_message, datetime.now(), transfer_id))
            else:
                sql = "UPDATE file_transfers SET status = %s WHERE id = %s"
                cursor.execute(sql, (status, transfer_id))
            
            conn.commit()
            print(f"[FileTransferManager] Updated transfer #{transfer_id} status: {status}")
            
        except Exception as e:
            print(f"[FileTransferManager] Error updating transfer status: {e}")
        finally:
            cursor.close()
            conn.close()
    
    def get_transfer_history(self, entity_id: str, entity_type: str, 
                           limit: int = 50) -> list:
        """
        Lấy lịch sử transfer của một entity (manager hoặc client)
        """
        conn = self._get_db_connection()
        if not conn:
            return []
            
        try:
            cursor = conn.cursor(dictionary=True)
            sql = """
                SELECT * FROM file_transfers 
                WHERE (sender_id = %s AND sender_type = %s) 
                   OR (receiver_id = %s AND receiver_type = %s)
                ORDER BY created_at DESC
                LIMIT %s
            """
            cursor.execute(sql, (entity_id, entity_type, entity_id, entity_type, limit))
            results = cursor.fetchall()
            return results
        except Exception as e:
            print(f"[FileTransferManager] Error getting transfer history: {e}")
            return []
        finally:
            cursor.close()
            conn.close()
    
    def get_all_transfers(self, limit: int = 100) -> list:
        """Lấy tất cả lịch sử transfer (cho admin)"""
        conn = self._get_db_connection()
        if not conn:
            return []
            
        try:
            cursor = conn.cursor(dictionary=True)
            sql = """
                SELECT * FROM file_transfers 
                ORDER BY created_at DESC
                LIMIT %s
            """
            cursor.execute(sql, (limit,))
            results = cursor.fetchall()
            return results
        except Exception as e:
            print(f"[FileTransferManager] Error getting all transfers: {e}")
            return []
        finally:
            cursor.close()
            conn.close()
    
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
