"""
File Transfer Handler - Xử lý logic nhận và chuyển tiếp file
"""

import json
import struct
from src.server.server_constants import (
    CMD_FILE_TRANSFER_ERROR, CMD_FILE_TRANSFER_ACK, CMD_FILE_TRANSFER_COMPLETE,
    CHANNEL_FILE
)

class FileTransferHandler:
    """Handle file transfer PDU processing"""
    
    @staticmethod
    def handle_file_pdu(session_manager, sender_id, pdu):
        """
        Xử lý file data PDU từ sender
        Nhận các chunks của file và forward tới receiver
        Hoặc xử lý violation screenshot từ AI Monitor
        """
        try:
            pdu_type = pdu.get("type", "")
            print(f"[FileTransfer] ===== RECEIVED FILE PDU =====")
            print(f"[FileTransfer] From: {sender_id}, Type: {pdu_type}")
            
            # Xử lý file_chunk PDU (format mới từ PDUBuilder)
            if pdu_type == "file_chunk":
                file_data = pdu.get("data", b"")  # Data đã được parse
                print(f"[FileTransfer] file_chunk data size: {len(file_data) if file_data else 0}")
                
                # Kiểm tra xem có phải violation screenshot không
                if FileTransferHandler._handle_violation_screenshot(session_manager, sender_id, file_data):
                    return  # Đã xử lý violation, không cần xử lý file transfer
            else:
                # Legacy format hoặc raw payload
                file_data = pdu.get("_raw_payload")  # Raw bytes
                print(f"[FileTransfer] raw_payload size: {len(file_data) if file_data else 0}")
            
            if not file_data:
                print(f"[FileTransfer] No file data in PDU from {sender_id}, type={pdu_type}")
                return
            
            # Prepare variables for use outside lock
            should_forward = False
            file_data_with_metadata = None
            transfer_id = None
            receiver_id = None
            filename = None
            
            # Kiểm tra và update pending transfer (trong lock)
            with session_manager.lock:
                print(f"[FileTransfer] Pending transfers: {list(session_manager.pending_file_transfers.keys())}")
                if sender_id not in session_manager.pending_file_transfers:
                    print(f"[FileTransfer] No pending transfer for {sender_id}")
                    return
                
                transfer_info = session_manager.pending_file_transfers[sender_id]
                transfer_id = transfer_info['transfer_id']
                receiver_id = transfer_info['receiver_id']
                filename = transfer_info['filename']
                filesize = transfer_info['filesize']
                
                # Lưu chunk
                transfer_info['chunks'].append(file_data)
                transfer_info['received_bytes'] += len(file_data)
                
                print(f"[FileTransfer] Received chunk: {len(file_data)} bytes "
                      f"({transfer_info['received_bytes']}/{filesize})")
                
                # Kiểm tra xem đã nhận đủ chưa
                if transfer_info['received_bytes'] >= filesize:
                    # Ghép tất cả chunks
                    complete_file = b''.join(transfer_info['chunks'])
                    
                    # Verify file hash if provided
                    if transfer_info.get('file_hash'):
                        calculated_hash = session_manager.file_transfer_manager.calculate_file_hash(complete_file)
                        if calculated_hash != transfer_info['file_hash']:
                            print(f"[FileTransfer] Hash mismatch for transfer #{transfer_id}")
                            session_manager.file_transfer_manager.fail_transfer(transfer_id, "Hash verification failed")
                            session_manager._send_control_pdu(sender_id, 
                                f"{CMD_FILE_TRANSFER_ERROR}:{transfer_id}:Hash mismatch")
                            del session_manager.pending_file_transfers[sender_id]
                            return
                    
                    # Prepare metadata
                    print(f"[FileTransfer] Forwarding file to {receiver_id}")
                    
                    metadata = {
                        'filename': filename,
                        'filesize': len(complete_file),
                        'sender_id': session_manager.authenticated_users.get(sender_id, sender_id),
                        'transfer_id': transfer_id
                    }
                    metadata_bytes = json.dumps(metadata).encode('utf-8')
                    metadata_len = len(metadata_bytes)
                    
                    # Tạo file data với metadata prefix
                    file_data_with_metadata = struct.pack('>I', metadata_len) + metadata_bytes + complete_file
                    
                    # Xóa khỏi pending
                    del session_manager.pending_file_transfers[sender_id]
                    should_forward = True
                else:
                    # Chưa nhận đủ - gửi ACK
                    progress = int(transfer_info['received_bytes'] * 100 / filesize)
                    session_manager._send_control_pdu(sender_id, 
                        f"{CMD_FILE_TRANSFER_ACK}:{transfer_id}:{progress}")
                    return
            
            # NGOÀI LOCK - Forward file tới receiver
            if should_forward and file_data_with_metadata:
                try:
                    from src.common.network.pdu_builder import PDUBuilder
                    from src.common.network.mcs_layer import MCSLite
                    
                    # Note: MCS layer giới hạn 65535 bytes
                    chunk_size = 32 * 1024  # 32KB chunks (để tránh vượt quá MCS limit)
                    total_sent = 0
                    seq = session_manager._next_seq()
                    
                    print(f"[FileTransfer] Starting to send {len(file_data_with_metadata)} bytes to {receiver_id}")
                    
                    while total_sent < len(file_data_with_metadata):
                        chunk = file_data_with_metadata[total_sent:total_sent + chunk_size]
                        
                        # Build proper FILE_CHUNK PDU
                        file_chunk_pdu = PDUBuilder.build_file_chunk(seq, total_sent, chunk)
                        seq += 1
                        
                        # Build MCS frame
                        mcs_frame = MCSLite.build(CHANNEL_FILE, file_chunk_pdu)
                        
                        # Gửi tới receiver
                        session_manager.broadcaster.enqueue(receiver_id, mcs_frame)
                        total_sent += len(chunk)
                        print(f"[FileTransfer] Sent chunk: {total_sent}/{len(file_data_with_metadata)} bytes")
                    
                    print(f"[FileTransfer] ✅ Sent file to {receiver_id}, total size: {len(file_data_with_metadata)} bytes")
                    
                    # Update database
                    session_manager.file_transfer_manager.complete_transfer(transfer_id)
                    
                    # Thông báo hoàn thành
                    session_manager._send_control_pdu(sender_id, 
                        f"{CMD_FILE_TRANSFER_COMPLETE}:{transfer_id}:{filename}")
                    session_manager._send_control_pdu(receiver_id, 
                        f"{CMD_FILE_TRANSFER_COMPLETE}:{filename}:Từ {session_manager.authenticated_users.get(sender_id, sender_id)}")
                    
                    print(f"[FileTransfer] Transfer #{transfer_id} completed: {filename}")
                    
                except Exception as send_error:
                    print(f"[FileTransfer] Error sending file to receiver: {send_error}")
                    import traceback
                    traceback.print_exc()
                    session_manager._send_control_pdu(sender_id, f"{CMD_FILE_TRANSFER_ERROR}:Failed to send to receiver")
        
        except Exception as e:
            print(f"[FileTransfer] Error handling file PDU: {e}")
            import traceback
            traceback.print_exc()
            
            # Cleanup on error
            with session_manager.lock:
                if sender_id in session_manager.pending_file_transfers:
                    transfer_id = session_manager.pending_file_transfers[sender_id]['transfer_id']
                    session_manager.file_transfer_manager.fail_transfer(transfer_id, str(e))
                    del session_manager.pending_file_transfers[sender_id]
    
    @staticmethod
    def _handle_violation_screenshot(session_manager, sender_id, file_data: bytes) -> bool:
        """
        Kiểm tra và xử lý violation screenshot từ AI Monitor
        
        Args:
            session_manager: SessionManager instance
            sender_id: ID của client gửi
            file_data: Data từ file_chunk PDU
            
        Returns:
            bool: True nếu đã xử lý violation screenshot, False nếu không phải
        """
        try:
            # File data format: [metadata_len(4 bytes)][metadata_json][image_data]
            if len(file_data) < 4:
                return False
            
            metadata_len = struct.unpack('>I', file_data[:4])[0]
            
            # Sanity check: metadata không quá lớn
            if metadata_len > 10000 or metadata_len + 4 > len(file_data):
                return False
            
            try:
                metadata_json = file_data[4:4+metadata_len].decode('utf-8')
                metadata = json.loads(metadata_json)
            except (UnicodeDecodeError, json.JSONDecodeError):
                return False
            
            # Kiểm tra xem có phải violation screenshot không
            if metadata.get('type') != 'violation_screenshot':
                return False
            
            # Đây là violation screenshot - xử lý
            print(f"[FileTransfer] 🚨 RECEIVED VIOLATION SCREENSHOT from {sender_id}")
            print(f"[FileTransfer] Metadata: {metadata}")
            
            # Extract image data
            image_data = file_data[4+metadata_len:]
            
            if len(image_data) == 0:
                print(f"[FileTransfer] ⚠️ No image data in violation screenshot")
                return True
            
            # Lấy thông tin từ metadata
            class_name = metadata.get('class_name', 'unknown')
            confidence = metadata.get('confidence', 0.0)
            username = metadata.get('username') or session_manager.authenticated_users.get(sender_id, sender_id)
            
            # Lưu vào violation storage
            try:
                result = session_manager.violation_storage.save_violation(
                    username=username,
                    violation_type=class_name,
                    confidence=confidence,
                    image_data=image_data,
                    additional_info={
                        'ai_timestamp': metadata.get('timestamp'),
                        'sender_id': sender_id
                    }
                )
                if result:
                    print(f"[FileTransfer] ✅ Saved violation screenshot: {result}")
                else:
                    print(f"[FileTransfer] ❌ Failed to save violation screenshot")
            except Exception as save_error:
                print(f"[FileTransfer] ❌ Error saving violation: {save_error}")
            
            return True
            
        except Exception as e:
            print(f"[FileTransfer] Error checking violation screenshot: {e}")
            return False
            session_manager._send_control_pdu(sender_id, f"{CMD_FILE_TRANSFER_ERROR}:Server error")
