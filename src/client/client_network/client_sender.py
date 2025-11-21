# client/client_network/client_sender.py

import threading
import queue
import time
import os
import json
import zlib
from typing import Optional, Dict, Any

from common_network.mcs_layer import MCSLite
from common_network.pdu_builder import PDUBuilder
from common_network.durable_queue import DurableQueue
from common_network.file_utils import stream_file_in_chunks, crc32_bytes
from common_network.pdu_parser import PDUParser 
from client.client_constants import CHANNEL_VIDEO, CHANNEL_FILE
# [QUAN TRỌNG] Import các hằng số cần thiết
from common_network.constants import SHARE_HDR_SIZE, FRAGMENT_HDR_SIZE, MAX_TPKT_LENGTH

class ClientSender:
    def __init__(self, 
                 network, 
                 channel_screen: int = CHANNEL_VIDEO, 
                 channel_file: int = CHANNEL_FILE,
                 max_unacked_bytes: int = 10 * 1024 * 1024,
                 frame_queue_size: int = 6):
        
        self.network = network 
        self.channel_screen = channel_screen
        self.channel_file = channel_file

        self.frame_q = queue.Queue(maxsize=frame_queue_size)
        
        self.dq = DurableQueue(db_path="client_durable_queue.db") 

        self.parser = PDUParser() 

        self._seq_lock = threading.Lock()
        self._seq = int(time.time()) & 0xffffffff

        self.unacked_bytes = 0
        self.unacked_lock = threading.Lock()
        self.max_unacked_bytes = max_unacked_bytes

        self._running = False
        self._frame_thread = None
        self._resend_thread = None 

        self.file_sessions: Dict[str, Dict[str, Any]] = {}

    def next_seq(self) -> int:
        with self._seq_lock:
            self._seq = (self._seq + 1) & 0xffffffff
            return self._seq

    def enqueue_frame(self, width: int, height: int, jpg_bytes: bytes, bbox=None, seq: Optional[int]=None, ts_ms: Optional[int]=None):
        if not self._running:
            return False
        try:
            if seq is None: seq = self.next_seq()
            if ts_ms is None: ts_ms = int(time.time() * 1000)
            
            # Gửi non-blocking
            self.frame_q.put_nowait((width, height, jpg_bytes, bbox, seq, ts_ms))
            return True
        except queue.Full:
            # Nếu queue đầy, bỏ frame cũ nhất
            try:
                self.frame_q.get_nowait() 
                self.frame_q.put_nowait((width, height, jpg_bytes, bbox, seq, ts_ms)) 
                return True
            except Exception:
                return False 

    def start(self):
        if self._running:
            return
        self._running = True
        
        self._frame_thread = threading.Thread(target=self._frame_sender_loop, daemon=True)
        self._frame_thread.start()
        self._resend_thread = threading.Thread(target=self._resend_loop, daemon=True)
        self._resend_thread.start()

    def stop(self):
        self._running = False
        if self._frame_thread and self._frame_thread.is_alive():
            self._frame_thread.join(timeout=1.0)
        if self._resend_thread and self._resend_thread.is_alive():
            self._resend_thread.join(timeout=1.0)

    def _frame_sender_loop(self):
        # TPKT Overhead = 4 bytes. MCS Header = 4 bytes. Tổng Header = 8 bytes.
        # PDU tối đa (Max MCS payload) = MAX_TPKT_LENGTH - 4 (TPKT Header) - 4 (MCS Header) = 65527
        MAX_FRAGMENT_SIZE = MAX_TPKT_LENGTH - 8 
        MAX_BODY_SIZE_PER_FRAGMENT = 64000
        
        while self._running:
            try:
                width, height, jpg, bbox, seq, ts_ms = self.frame_q.get(timeout=0.1) 
            except queue.Empty:
                continue
            
            try:
                # 1. Tạo PDU (Luôn là FULL Frame theo logic mới)
                if bbox:
                    # Logic này có thể không bao giờ chạy nếu bbox luôn None
                    l, u, r, b = bbox
                    w, h = r - l, b - u
                    pdu = PDUBuilder.build_rect_frame_pdu(seq, jpg, l, u, w, h, width, height, flags=0)
                else:
                    pdu = PDUBuilder.build_full_frame_pdu(seq, jpg, width, height, flags=0)

                # 2. Gửi (Có phân mảnh)
                # Nếu PDU lớn hơn kích thước cho phép, phải chia nhỏ
                if len(pdu) > MAX_BODY_SIZE_PER_FRAGMENT:
                    fragments = PDUBuilder.fragmentize(pdu, MAX_BODY_SIZE_PER_FRAGMENT)
                    
                    for offset, frag_bytes in fragments:
                        if not self._running: break
                        self.network.send_mcs_pdu(self.channel_screen, frag_bytes)
                        # Sleep cực ngắn để tránh nghẽn socket buffer
                        time.sleep(0.0005) 
                else:
                    # Gửi nguyên cục
                    self.network.send_mcs_pdu(self.channel_screen, pdu)
                        
            except Exception as e:
                print(f"[ClientSender] Lỗi gửi frame: {e}")
                time.sleep(0.1)

    def send_file(self, filepath: str, chunk_size: int = 32 * 1024):
        if not os.path.exists(filepath):
            raise FileNotFoundError(filepath)
        t = threading.Thread(target=self._send_file_thread, args=(filepath, chunk_size), daemon=True)
        t.start()
        return t

    def _send_file_thread(self, filepath: str, chunk_size: int):
        filename = os.path.basename(filepath)
        total_size = os.path.getsize(filepath)
        crc = 0
        try:
            with open(filepath, "rb") as f:
                while True:
                    b = f.read(65536)
                    if not b: break
                    crc = zlib.crc32(b, crc)
        except Exception as e:
            print(f"Không thể đọc file {filepath}: {e}")
            return
        crc &= 0xffffffff

        self.file_sessions[filename] = {
            "total": total_size, "crc": crc, "last_ack": 0, "chunk_size": chunk_size
        }

        seq = self.next_seq()
        start_pdu = PDUBuilder.build_file_start(seq, filename, total_size, chunk_size, crc)
        self.network.send_mcs_pdu(self.channel_file, start_pdu)

        for offset, chunk in stream_file_in_chunks(filepath, chunk_size):
            if not self._running: break
            seq = self.next_seq()
            pdu = PDUBuilder.build_file_chunk(seq, offset, chunk)
            self.dq.push(pdu) 

        if self._running:
            seq = self.next_seq()
            end_pdu = PDUBuilder.build_file_end(seq, crc)
            self.network.send_mcs_pdu(self.channel_file, end_pdu)
    
    def handle_file_ack(self, pdu: Dict[str, Any]):
        try:
            ack_offset = pdu.get("ack_offset", 0)
            self._process_file_ack(ack_offset)
        except Exception as e:
            print(f"[ClientSender] Lỗi xử lý ACK: {e}")

    def _process_file_ack(self, ack_offset: int):
        removed_bytes = 0
        while self._running:
            entry = self.dq.peek()
            if not entry:
                break 
            
            qid, pdu_bytes = entry
            try:
                parsed = self.parser.parse(pdu_bytes)
                if not parsed or parsed.get("type") != "file_chunk":
                    self.dq.pop(qid)
                    continue

                offset = parsed.get("offset", 0)
                length = len(parsed.get("data", b""))

                if (offset + length) <= ack_offset:
                    self.dq.pop(qid) 
                    removed_bytes += length
                else:
                    break
            except Exception as e:
                print(f"[ClientSender] Lỗi parse PDU từ DB: {e}, xóa PDU hỏng.")
                self.dq.pop(qid) 

        if removed_bytes > 0:
            with self.unacked_lock:
                self.unacked_bytes = max(0, self.unacked_bytes - removed_bytes)

    def handle_file_nak(self, pdu: Dict[str, Any]):
        reason = pdu.get("reason", b"")
        off = pdu.get("offset", 0)
        print(f"[ClientSender] Nhận NAK offset={off} reason={reason}")

    def _resend_loop(self):
        while self._running:
            try:
                if not self.network.running or not self.network.client:
                    time.sleep(1.0)
                    continue

                entry = self.dq.peek() 
                if not entry:
                    time.sleep(0.5) 
                    continue
                
                qid, payload_pdu = entry
                
                length = 0
                try:
                    parsed = self.parser.parse(payload_pdu)
                    if not parsed or parsed.get("type") != "file_chunk":
                        self.dq.pop(qid)
                        continue
                    length = len(parsed.get("data", b""))
                except Exception:
                    self.dq.pop(qid)
                    continue

                can_send = False
                with self.unacked_lock:
                    if self.unacked_bytes + length <= self.max_unacked_bytes:
                        self.unacked_bytes += length 
                        can_send = True
                
                if not can_send:
                    time.sleep(0.1) 
                    continue
                    
                try:
                    self.network.send_mcs_pdu(self.channel_file, payload_pdu)
                    time.sleep(0.1) 

                except Exception as e:
                    print(f"[ClientSender] Lỗi gửi lại: {e}")
                    with self.unacked_lock:
                        self.unacked_bytes = max(0, self.unacked_bytes - length)
                    time.sleep(1.0) 
                    
            except Exception as e:
                print(f"[ClientSender] Lỗi resend loop (peek): {e}")
                time.sleep(1.0)