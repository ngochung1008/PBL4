"""
Client File Transfer Module - Gửi và nhận file từ/tới manager
"""

import os
import hashlib
import threading
from typing import Optional, Callable


class ClientFileTransfer:
    """Quản lý việc gửi và nhận file cho client"""
    
    def __init__(self, sender, receiver):
        """
        Args:
            sender: ClientSender instance để gửi file
            receiver: ClientReceiver instance để nhận callback
        """
        self.sender = sender
        self.receiver = receiver
        self.on_file_received = None  # Callback khi nhận file (filename, filepath)
        self.on_progress = None  # Callback progress (int)
        self.on_complete = None  # Callback khi gửi xong ()
        self.on_error = None  # Callback khi lỗi (error_msg)
        
        # Storage cho received files
        self.received_files_dir = "src/client/file_transfer/received"
        os.makedirs(self.received_files_dir, exist_ok=True)
        
        # Active transfers
        self.active_sends = {}  # {transfer_id: file_info}
        self.lock = threading.Lock()
    
    def send_file(self, target_id: str, filepath: str) -> bool:
        """
        Gửi file tới target (manager hoặc client khác)
        
        Args:
            target_id: Username hoặc ID của người nhận
            filepath: Đường dẫn file cần gửi
            
        Returns:
            True nếu bắt đầu gửi thành công
        """
        if not os.path.exists(filepath):
            print(f"[ClientFileTransfer] File không tồn tại: {filepath}")
            if self.on_error:
                self.on_error("File không tồn tại")
            return False
        
        try:
            filename = os.path.basename(filepath)
            filesize = os.path.getsize(filepath)
            
            # Đọc file và tính hash
            with open(filepath, 'rb') as f:
                file_data = f.read()
            
            file_hash = hashlib.sha256(file_data).hexdigest()
            
            print(f"[ClientFileTransfer] Preparing to send: {filename} ({filesize} bytes)")
            
            # Gửi control message yêu cầu transfer
            from src.server.server_constants import CMD_SEND_FILE
            control_msg = f"{CMD_SEND_FILE}:{target_id}:{filename}:{filesize}:{file_hash}"
            
            # Gửi qua sender control channel
            if hasattr(self.sender, 'send_control'):
                self.sender.send_control(control_msg)
            else:
                # Fallback: gửi qua network trực tiếp
                from src.common.network.pdu_builder import PDUBuilder
                from src.client.client_constants import CHANNEL_CONTROL
                builder = PDUBuilder()
                seq = self.sender.next_seq()
                pdu = builder.build_control(seq, control_msg.encode('utf-8'))
                self.sender.network.send_pdu(CHANNEL_CONTROL, pdu)
            
            # Lưu thông tin để gửi file sau khi nhận ACK
            with self.lock:
                self.active_sends[target_id] = {
                    'filepath': filepath,
                    'filename': filename,
                    'filesize': filesize,
                    'file_data': file_data,
                    'file_hash': file_hash
                }
            
            print(f"[ClientFileTransfer] Sent file transfer request")
            return True
            
        except Exception as e:
            print(f"[ClientFileTransfer] Error sending file: {e}")
            if self.on_error:
                self.on_error(str(e))
            return False
    
    def handle_file_transfer_ack(self, message: str):
        """
        Xử lý ACK từ server - bắt đầu gửi file data
        
        Args:
            message: Message dạng "file_transfer_start:transfer_id" hoặc "file_transfer_ack:..."
        """
        # Parse message
        parts = message.split(":")
        if len(parts) < 2:
            print(f"[ClientFileTransfer] Invalid ACK message: {message}")
            return
        
        cmd = parts[0]
        transfer_id = parts[1] if len(parts) > 1 else "0"
        
        if cmd == "file_transfer_start":
            # Server đã sẵn sàng nhận file
            print(f"[ClientFileTransfer] Received file_transfer_start ACK for transfer #{transfer_id}")
            self._send_file_chunks()
        elif cmd == "file_transfer_ack":
            # Progress update
            print(f"[ClientFileTransfer] Received progress ACK: {message}")
        else:
            print(f"[ClientFileTransfer] Unknown ACK command: {cmd}")
    
    def _send_file_chunks(self):
        """Gửi file data chunks sau khi nhận ACK"""
        with self.lock:
            # Tìm pending transfer (có thể dùng target_id làm key tạm thời)
            if not self.active_sends:
                print(f"[ClientFileTransfer] No active sends to process")
                return
            
            # Lấy transfer đầu tiên (giả sử chỉ gửi 1 file tại 1 thời điểm)
            target_id = list(self.active_sends.keys())[0]
            file_info = self.active_sends[target_id]
            file_data = file_info['file_data']
            filename = file_info['filename']
        
        print(f"[ClientFileTransfer] Received ACK, sending file data...")
        
        # Gửi file data qua CHANNEL_FILE
        try:
            from src.client.client_constants import CHANNEL_FILE
            from src.common.network.pdu_builder import PDUBuilder
            
            # Chia file thành chunks nếu cần
            chunk_size = 64 * 1024  # 64KB chunks
            total_sent = 0
            
            while total_sent < len(file_data):
                chunk = file_data[total_sent:total_sent + chunk_size]
                
                # Tạo file PDU
                builder = PDUBuilder()
                seq = self.sender.next_seq()
                
                # Build simple file chunk PDU
                file_pdu_header = builder._hdr(seq, 5, 0)  # 5 = file type
                file_pdu = file_pdu_header + chunk
                
                # Gửi
                self.sender.network.send_pdu(CHANNEL_FILE, file_pdu)
                
                total_sent += len(chunk)
                
                # Report progress
                if self.on_progress:
                    progress = int(total_sent * 100 / len(file_data))
                    self.on_progress(progress)
                
                print(f"[ClientFileTransfer] Sent {total_sent}/{len(file_data)} bytes")
            
            print(f"[ClientFileTransfer] File data sent completely")
            
        except Exception as e:
            print(f"[ClientFileTransfer] Error sending file data: {e}")
            if self.on_error:
                self.on_error(str(e))
    
    def handle_file_received(self, metadata: dict, file_data: bytes):
        """
        Xử lý khi nhận được file từ server
        
        Args:
            metadata: Dict chứa filename, sender_id, etc.
            file_data: Dữ liệu file
        """
        try:
            filename = metadata.get('filename', 'unknown_file')
            sender_id = metadata.get('sender_id', 'unknown')
            
            # Lưu file
            safe_filename = os.path.basename(filename)  # Bảo mật: chỉ lấy tên file
            save_path = os.path.join(self.received_files_dir, safe_filename)
            
            # Tránh ghi đè: thêm số nếu file đã tồn tại
            counter = 1
            base_name, ext = os.path.splitext(safe_filename)
            while os.path.exists(save_path):
                safe_filename = f"{base_name}_{counter}{ext}"
                save_path = os.path.join(self.received_files_dir, safe_filename)
                counter += 1
            
            with open(save_path, 'wb') as f:
                f.write(file_data)
            
            print(f"[ClientFileTransfer] File saved: {save_path}")
            
            # Callback
            if self.on_file_received:
                self.on_file_received(safe_filename, save_path)
            
        except Exception as e:
            print(f"[ClientFileTransfer] Error saving received file: {e}")
    
    def handle_file_pdu(self, pdu: dict):
        """
        Xử lý FILE PDU từ server - nhận file chunks
        
        Args:
            pdu: Dict chứa file data từ server
        """
        try:
            # Giả sử pdu có dạng: {'data': bytes, 'metadata': {...}}
            file_data = pdu.get('data', b'')
            metadata = pdu.get('metadata', {})
            
            if file_data:
                print(f"[ClientFileTransfer] Received file PDU: {len(file_data)} bytes")
                # Nhận và lưu file
                self.handle_file_received(metadata, file_data)
            else:
                print(f"[ClientFileTransfer] Empty file PDU received")
                
        except Exception as e:
            print(f"[ClientFileTransfer] Error handling file PDU: {e}")
            if self.on_error:
                self.on_error(f"Error receiving file: {e}")
    
    def handle_transfer_complete(self, transfer_id: str, filename: str):
        """Xử lý thông báo transfer hoàn thành"""
        print(f"[ClientFileTransfer] Transfer #{transfer_id} completed: {filename}")
        
        # Cleanup
        with self.lock:
            # Remove from active sends
            for target_id in list(self.active_sends.keys()):
                if self.active_sends[target_id]['filename'] == filename:
                    del self.active_sends[target_id]
                    break
        
        if self.on_complete:
            self.on_complete()
    
    def handle_transfer_error(self, error_msg: str):
        """Xử lý lỗi transfer"""
        print(f"[ClientFileTransfer] Transfer error: {error_msg}")
        
        # Cleanup all active sends
        with self.lock:
            self.active_sends.clear()
        
        if self.on_error:
            self.on_error(error_msg)
