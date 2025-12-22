"""
Client File Transfer Module - Gửi và nhận file từ/tới manager
"""

import os
import hashlib
import threading
import time
from typing import Optional, Callable


class ClientFileTransfer:
    """Quản lý việc gửi và nhận file cho client"""
    
    def __init__(self, sender, logger=None):
        """
        Args:
            sender: ClientSender instance để gửi file
            logger: Logger function (optional)
        """
        self.sender = sender
        self.logger = logger or print
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
        
        # Receiving file chunks buffer
        self.receiving_chunks = []  # Buffer để lắp ráp các chunks
        self.receiving_total_size = 0  # Tổng bytes đã nhận
    
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
            self._call_error_callback("File không tồn tại")
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
            
            # Gửi qua network control channel
            self.sender.network.send_control_pdu(control_msg)
            
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
            self._call_error_callback(str(e))
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
        
        print(f"[ClientFileTransfer] Starting to send file chunks...")
        
        # Gửi file data qua CHANNEL_FILE
        try:
            from src.client.client_constants import CHANNEL_FILE
            from src.common.network.pdu_builder import PDUBuilder
            
            # Chia file thành chunks nếu cần
            chunk_size = 64 * 1024  # 64KB chunks
            total_sent = 0
            chunk_num = 0
            seq = 1  # Sequence number cho PDU
            
            while total_sent < len(file_data):
                chunk = file_data[total_sent:total_sent + chunk_size]
                
                # Build proper FILE_CHUNK PDU với header đúng
                file_chunk_pdu = PDUBuilder.build_file_chunk(seq, total_sent, chunk)
                seq += 1
                
                # Gửi chunk qua FILE channel
                self.sender.network.send_mcs_pdu(CHANNEL_FILE, file_chunk_pdu)
                
                total_sent += len(chunk)
                chunk_num += 1
                
                # Report progress
                progress = int(total_sent * 100 / len(file_data))
                if self.on_progress:
                    self.on_progress(progress)
                
                print(f"[ClientFileTransfer] Sent chunk {chunk_num}: {total_sent}/{len(file_data)} bytes ({progress}%)")
                
                # Small delay to avoid overwhelming
                time.sleep(0.01)
            
            print(f"[ClientFileTransfer] File data sent completely: {len(file_data)} bytes")
            
        except Exception as e:
            print(f"[ClientFileTransfer] Error sending file data: {e}")
            self._call_error_callback(str(e))
    
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
            
            # Callback - use thread-safe invocation
            if self.on_file_received:
                # Call directly if no GUI context, otherwise caller should handle thread safety
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
            pdu_type = pdu.get('type')
            print(f"[ClientFileTransfer] ===== Received FILE PDU =====")
            print(f"[ClientFileTransfer] PDU type: {pdu_type}")
            
            # Xử lý file_chunk PDU
            if pdu_type == 'file_chunk':
                chunk_data = pdu.get('data', b'')
                offset = pdu.get('offset', 0)
                
                if chunk_data:
                    print(f"[ClientFileTransfer] Received chunk at offset {offset}, size: {len(chunk_data)} bytes")
                    
                    with self.lock:
                        # Thêm chunk vào buffer
                        self.receiving_chunks.append((offset, chunk_data))
                        self.receiving_total_size += len(chunk_data)
                    
                    # Kiểm tra nếu đây là chunk đầu tiên (offset=0) → chứa metadata
                    if offset == 0:
                        # Thử parse metadata từ chunk đầu tiên
                        self._try_complete_file_from_chunks()
                    else:
                        # Thử lắp ráp file nếu đã nhận đủ chunks
                        self._try_complete_file_from_chunks()
                return
            
            # Legacy format support
            file_data = None
            metadata = {}
            
            if 'data' in pdu:
                file_data = pdu.get('data', b'')
                metadata = pdu.get('metadata', {})
            elif '_raw_payload' in pdu:
                raw = pdu.get('_raw_payload', b'')
                if len(raw) > 0:
                    file_data = raw
                    metadata = {
                        'filename': pdu.get('filename', 'received_file'),
                        'sender_id': pdu.get('sender_id', 'unknown')
                    }
            
            if file_data and len(file_data) > 0:
                print(f"[ClientFileTransfer] Received file data (legacy): {len(file_data)} bytes")
                self.handle_file_received(metadata, file_data)
            else:
                print(f"[ClientFileTransfer] No file data in PDU")
                
        except Exception as e:
            print(f"[ClientFileTransfer] Error handling file PDU: {e}")
            import traceback
            traceback.print_exc()
            self._call_error_callback(f"Error receiving file: {e}")
    
    def _try_complete_file_from_chunks(self):
        """Thử lắp ráp file từ các chunks đã nhận"""
        import struct
        import json
        
        with self.lock:
            if not self.receiving_chunks:
                return
            
            # Sắp xếp chunks theo offset
            sorted_chunks = sorted(self.receiving_chunks, key=lambda x: x[0])
            
            # Ghép tất cả chunks
            complete_data = b''.join([chunk for _, chunk in sorted_chunks])
            
            # Kiểm tra có metadata không (4 bytes đầu là metadata_len)
            if len(complete_data) < 4:
                return  # Chưa đủ data
            
            try:
                metadata_len = struct.unpack('>I', complete_data[:4])[0]
                
                # Kiểm tra đã nhận đủ metadata + file_data chưa
                if len(complete_data) < 4 + metadata_len:
                    return  # Chưa đủ data
                
                metadata_bytes = complete_data[4:4+metadata_len]
                file_data = complete_data[4+metadata_len:]
                
                metadata = json.loads(metadata_bytes.decode('utf-8'))
                expected_filesize = metadata.get('filesize', 0)
                
                print(f"[ClientFileTransfer] Parsed metadata: {metadata}")
                print(f"[ClientFileTransfer] Expected filesize: {expected_filesize}, received: {len(file_data)}")
                
                # Kiểm tra đã nhận đủ file chưa
                if len(file_data) >= expected_filesize:
                    # Đã nhận đủ → lưu file
                    print(f"[ClientFileTransfer] File complete! Saving...")
                    
                    # Lấy đúng kích thước file (không lấy padding)
                    file_data = file_data[:expected_filesize]
                    
                    self.handle_file_received(metadata, file_data)
                    
                    # Reset buffer
                    self.receiving_chunks = []
                    self.receiving_total_size = 0
                    
            except (struct.error, json.JSONDecodeError) as e:
                # Có thể chưa nhận đủ metadata, tiếp tục chờ
                print(f"[ClientFileTransfer] Waiting for more chunks... ({e})")
                pass
    
    def _call_progress_callback(self, progress: int):
        """Thread-safe progress callback"""
        if self.on_progress:
            self.on_progress(progress)
    
    def _call_complete_callback(self):
        """Thread-safe complete callback"""
        if self.on_complete:
            self.on_complete()
    
    def _call_error_callback(self, error_msg: str):
        """Thread-safe error callback"""
        if self.on_error:
            self.on_error(error_msg)
    
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
        
        self._call_error_callback(error_msg)
