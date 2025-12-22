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
        """
        try:
            # Lấy file data từ PDU
            file_data = pdu.get("_raw_payload")  # Raw bytes
            if not file_data:
                print(f"[FileTransfer] No file data in PDU from {sender_id}")
                return
            
            # Kiểm tra xem có pending transfer không
            with session_manager.lock:
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
                    
                    # Forward file tới receiver
                    print(f"[FileTransfer] Forwarding file to {receiver_id}")
                    
                    # Tạo metadata JSON
                    metadata = {
                        'filename': filename,
                        'filesize': len(complete_file),
                        'sender_id': session_manager.authenticated_users.get(sender_id, sender_id),
                        'transfer_id': transfer_id
                    }
                    metadata_bytes = json.dumps(metadata).encode('utf-8')
                    metadata_len = len(metadata_bytes)
                    
                    # Tạo file PDU: [metadata_len(4bytes)][metadata][file_data]
                    file_pdu_body = struct.pack('>I', metadata_len) + metadata_bytes + complete_file
                    
                    # Build PDU with header
                    pdu_header = session_manager.builder._hdr(session_manager._next_seq(), 5, 0)  # 5 = PDU type for file
                    full_pdu = pdu_header + file_pdu_body
                    
                    # Build MCS frame (channel_header + PDU)
                    from src.common.network.mcs_layer import MCSLite
                    mcs_frame = MCSLite.build(CHANNEL_FILE, full_pdu)
                    
                    # Gửi file tới receiver using enqueue
                    print(f"[FileTransfer] Sending file PDU to {receiver_id}, size: {len(mcs_frame)} bytes")
                    session_manager.broadcaster.enqueue(receiver_id, mcs_frame)
                    
                    # Update database
                    session_manager.file_transfer_manager.complete_transfer(transfer_id)
                    
                    # Thông báo hoàn thành
                    session_manager._send_control_pdu(sender_id, 
                        f"{CMD_FILE_TRANSFER_COMPLETE}:{transfer_id}:{filename}")
                    session_manager._send_control_pdu(receiver_id, 
                        f"{CMD_FILE_TRANSFER_COMPLETE}:{filename}:Từ {session_manager.authenticated_users.get(sender_id, sender_id)}")
                    
                    # Cleanup
                    del session_manager.pending_file_transfers[sender_id]
                    
                    print(f"[FileTransfer] Transfer #{transfer_id} completed: {filename}")
                else:
                    # Gửi ACK để sender biết đã nhận chunk
                    progress = int(transfer_info['received_bytes'] * 100 / filesize)
                    session_manager._send_control_pdu(sender_id, 
                        f"{CMD_FILE_TRANSFER_ACK}:{transfer_id}:{progress}")
        
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
            
            session_manager._send_control_pdu(sender_id, f"{CMD_FILE_TRANSFER_ERROR}:Server error")
