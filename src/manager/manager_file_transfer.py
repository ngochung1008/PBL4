"""
Manager File Transfer Module - Gửi và nhận file từ/tới client
"""

import os
import hashlib
import threading
from typing import Optional, Callable


class ManagerFileTransfer:
    """Quản lý việc gửi và nhận file cho manager"""
    
    def __init__(self, manager_app):
        """
        Args:
            manager_app: ManagerApp instance
        """
        self.app = manager_app
        self.on_file_received = None  # Callback khi nhận file
        self.on_file_send_progress = None  # Callback khi gửi file
        self.on_file_send_complete = None  # Callback khi gửi xong
        self.on_file_send_error = None  # Callback khi lỗi
        
        # Storage cho received files
        self.received_files_dir = "manager_received_files"
        os.makedirs(self.received_files_dir, exist_ok=True)
        
        # Active transfers
        self.active_sends = {}  # {target_id: file_info}
        self.lock = threading.Lock()
    
    def send_file(self, target_client_id: str, filepath: str) -> bool:
        """
        Gửi file tới client
        
        Args:
            target_client_id: Username hoặc ID của client
            filepath: Đường dẫn file cần gửi
            
        Returns:
            True nếu bắt đầu gửi thành công
        """
        if not os.path.exists(filepath):
            print(f"[ManagerFileTransfer] File không tồn tại: {filepath}")
            if self.on_file_send_error:
                self.on_file_send_error("File không tồn tại")
            return False
        
        try:
            filename = os.path.basename(filepath)
            filesize = os.path.getsize(filepath)
            
            # Đọc file và tính hash
            with open(filepath, 'rb') as f:
                file_data = f.read()
            
            file_hash = hashlib.sha256(file_data).hexdigest()
            
            print(f"[ManagerFileTransfer] Preparing to send: {filename} ({filesize} bytes)")
            
            # Gửi control message yêu cầu transfer
            from src.server.server_constants import CMD_SEND_FILE
            control_msg = f"{CMD_SEND_FILE}:{target_client_id}:{filename}:{filesize}:{file_hash}"
            
            # Gửi qua app
            self.app.send_control_message(control_msg)
            
            # Lưu thông tin để gửi file sau khi nhận ACK
            with self.lock:
                self.active_sends[target_client_id] = {
                    'filepath': filepath,
                    'filename': filename,
                    'filesize': filesize,
                    'file_data': file_data,
                    'file_hash': file_hash
                }
            
            print(f"[ManagerFileTransfer] Sent file transfer request")
            return True
            
        except Exception as e:
            print(f"[ManagerFileTransfer] Error sending file: {e}")
            if self.on_file_send_error:
                self.on_file_send_error(str(e))
            return False
    
    def handle_file_transfer_ack(self, transfer_id: str):
        """
        Xử lý ACK từ server - bắt đầu gửi file data
        """
        with self.lock:
            if not self.active_sends:
                print(f"[ManagerFileTransfer] No active sends for transfer #{transfer_id}")
                return
            
            # Lấy transfer đầu tiên
            target_id = list(self.active_sends.keys())[0]
            file_info = self.active_sends[target_id]
            file_data = file_info['file_data']
            filename = file_info['filename']
        
        print(f"[ManagerFileTransfer] Received ACK, sending file data...")
        
        # Gửi file data qua CHANNEL_FILE
        try:
            from src.manager.manager_constants import CHANNEL_FILE
            from src.common.network.pdu_builder import PDUBuilder
            
            # Chia file thành chunks
            chunk_size = 64 * 1024  # 64KB chunks
            total_sent = 0
            
            seq = 1  # Sequence number
            while total_sent < len(file_data):
                chunk = file_data[total_sent:total_sent + chunk_size]
                
                # Build proper FILE_CHUNK PDU (type=11, not 5)
                file_chunk_pdu = PDUBuilder.build_file_chunk(seq, total_sent, chunk)
                seq += 1
                
                # Gửi qua ManagerApp._send_mcs_pdu (ManagerApp không có .network)
                self.app._send_mcs_pdu(CHANNEL_FILE, file_chunk_pdu)
                
                total_sent += len(chunk)
                
                # Report progress
                if self.on_file_send_progress:
                    progress = int(total_sent * 100 / len(file_data))
                    self.on_file_send_progress(progress)
                
                print(f"[ManagerFileTransfer] Sent {total_sent}/{len(file_data)} bytes")
            
            print(f"[ManagerFileTransfer] File data sent completely")
            
        except Exception as e:
            print(f"[ManagerFileTransfer] Error sending file data: {e}")
            if self.on_file_send_error:
                self.on_file_send_error(str(e))
    
    def handle_file_received(self, metadata: dict, file_data: bytes):
        """
        Xử lý khi nhận được file từ server/client
        
        Args:
            metadata: Dict chứa filename, sender_id, etc.
            file_data: Dữ liệu file
        """
        try:
            filename = metadata.get('filename', 'unknown_file')
            sender_id = metadata.get('sender_id', 'unknown')
            
            # Lưu file
            safe_filename = os.path.basename(filename)
            save_path = os.path.join(self.received_files_dir, safe_filename)
            
            # Tránh ghi đè
            counter = 1
            base_name, ext = os.path.splitext(safe_filename)
            while os.path.exists(save_path):
                safe_filename = f"{base_name}_{counter}{ext}"
                save_path = os.path.join(self.received_files_dir, safe_filename)
                counter += 1
            
            with open(save_path, 'wb') as f:
                f.write(file_data)
            
            print(f"[ManagerFileTransfer] File saved: {save_path}")
            
            # Callback
            if self.on_file_received:
                self.on_file_received(filename, save_path, sender_id)
            
        except Exception as e:
            print(f"[ManagerFileTransfer] Error saving received file: {e}")
    
    def handle_transfer_complete(self, transfer_id: str, filename: str):
        """Xử lý thông báo transfer hoàn thành"""
        print(f"[ManagerFileTransfer] Transfer #{transfer_id} completed: {filename}")
        
        # Cleanup
        with self.lock:
            for target_id in list(self.active_sends.keys()):
                if self.active_sends[target_id]['filename'] == filename:
                    del self.active_sends[target_id]
                    break
        
        if self.on_file_send_complete:
            self.on_file_send_complete(filename)
    
    def handle_transfer_error(self, error_msg: str):
        """Xử lý lỗi transfer"""
        print(f"[ManagerFileTransfer] Transfer error: {error_msg}")
        
        # Cleanup
        with self.lock:
            self.active_sends.clear()
        
        if self.on_file_send_error:
            self.on_file_send_error(error_msg)
