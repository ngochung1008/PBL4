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
            pdu_type = pdu.get("type", "")
            
            # Xử lý file_chunk PDU (format mới từ PDUBuilder)
            if pdu_type == "file_chunk":
                file_data = pdu.get("data", b"")  # Data đã được parse
            else:
                # Legacy format hoặc raw payload
                file_data = pdu.get("_raw_payload")  # Raw bytes
            
            if not file_data:
                print(f"[FileTransfer] No file data in PDU from {sender_id}, type={pdu_type}")
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
                    
                    # Tạo file data với metadata prefix: [metadata_len(4bytes)][metadata][file_data]
                    file_data_with_metadata = struct.pack('>I', metadata_len) + metadata_bytes + complete_file
                    
                    # Gửi qua file chunks với proper PDU format
                    from src.common.network.pdu_builder import PDUBuilder
                    from src.common.network.mcs_layer import MCSLite
                    from src.common.network.tpkt_layer import TPKTLayer
                    
                    chunk_size = 64 * 1024  # 64KB chunks
                    total_sent = 0
                    seq = session_manager._next_seq()
                    
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
                    
                    print(f"[FileTransfer] Sent file to {receiver_id}, total size: {len(file_data_with_metadata)} bytes")
                    
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
