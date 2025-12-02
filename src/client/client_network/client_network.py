# client/client_network/client_network.py

import threading
import socket
import ssl
from queue import Queue, Empty
from time import time
from common_network.x224_handshake import X224Handshake, CONFIRM_MAGIC
from common_network.security_layer_tls import create_client_context, client_wrap_socket
from common_network.pdu_builder import PDUBuilder
from common_network.mcs_layer import MCSLite
from common_network.tpkt_layer import TPKTLayer
from client.client_network.client_receiver import ClientReceiver
from client.client_constants import (
    CLIENT_ID, CA_FILE, 
    CHANNEL_CONTROL, CHANNEL_INPUT, CHANNEL_VIDEO, CHANNEL_FILE, CHANNEL_CURSOR,
    CMD_REGISTER
)

class ClientNetwork:
    """
    Lớp chính quản lý kết nối (TLS, Handshake), luồng nhận (Receiver),
    và vòng lặp xử lý PDU.
    """

    def __init__(self, host, port, client_id=CLIENT_ID, cafile=CA_FILE, logger=None):
        self.host = host
        self.port = port
        self.client_id = client_id
        self.cafile = cafile
        self.logger = logger or print
        
        self.client = None # Sẽ là SSLSocket
        self.receiver = None
        self.running = False
        
        self.pdu_queue = Queue()
        self.pdu_loop_thread = None
        
        self.builder = PDUBuilder()
        self.seq = 0
        self.lock = threading.Lock() # Dùng cho self.seq và self.client

        # Callbacks cho lớp Client (UI/Glue)
        self.on_input_pdu = None
        self.on_control_pdu = None
        self.on_file_pdu = None
        self.on_file_ack = None
        self.on_file_nak = None
        self.on_disconnected = None

    def connect(self, timeout=20.0) -> bool:
        """Thực hiện kết nối: Raw -> X224 -> TLS"""
        raw_sock = None
        try:
            # 1. Kết nối socket thô
            raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            raw_sock.settimeout(timeout)
            raw_sock.connect((self.host, self.port))

            # 2. Thực hiện X224 Handshake
            resp = X224Handshake.client_send_connect(raw_sock, self.client_id, timeout=timeout)
            
            if not (isinstance(resp, bytes) and resp.startswith(CONFIRM_MAGIC)):
                self.logger(f"[ClientNetwork] Handshake X224 thất bại, resp: {resp}")
                raw_sock.close()
                return False
            self.logger("[ClientNetwork] Handshake X224 thành công.")

            # 3. Tạo TLS Context
            tls_context = create_client_context(cafile=self.cafile, check_hostname=False)

            # 4. Bọc (Wrap) socket thô lên SSLSocket
            self.client = client_wrap_socket(
                raw_sock,
                tls_context,
                server_hostname=self.host,
                timeout=timeout,
                do_handshake=True
            )
            
            self.client.settimeout(20.0) # Chuyển về blocking cho Receiver
            self.logger(f"[ClientNetwork] Kết nối TLS thành công tới {self.host}:{self.port}")
            return True

        except ssl.SSLError as e:
            self.logger(f"[ClientNetwork] Lỗi TLS Handshake: {e}. (Kiểm tra file '{self.cafile}')")
        except Exception as e:
            self.logger(f"[ClientNetwork] Lỗi kết nối: {e}")
        
        if self.client: self.client.close()
        if raw_sock: raw_sock.close()
        self.client = None
        return False

    def start(self) -> bool:
        if not self.connect():
            return False
        
        self.running = True
        
        # Khởi tạo Receiver
        self.receiver = ClientReceiver(self.client, self.pdu_queue, self._on_receiver_done)
        self.receiver.start()
        
        # Khởi tạo PDU loop
        self.pdu_loop_thread = threading.Thread(target=self._pdu_loop, daemon=True)
        self.pdu_loop_thread.start()
        
        self.logger("[ClientNetwork] Đã khởi động.")
        
        # Tự động đăng ký
        self.register()
        return True

    def stop(self):
        self.running = False
        if self.receiver:
            self.receiver.stop()
        if self.client:
            try: self.client.close()
            except: pass
        
        with self.pdu_queue.mutex:
            self.pdu_queue.queue.clear()
            
        self.logger("[ClientNetwork] Đã dừng.")
        if self.on_disconnected:
            self.on_disconnected() # Báo cho main loop biết
            
    def _on_receiver_done(self):
        """Callback từ Receiver khi mất kết nối"""
        if self.running:
            self.logger("[ClientNetwork] Mất kết nối tới server.")
            self.stop() # Tự động dọn dẹp

    def _pdu_loop(self):
        """Xử lý PDU từ queue và gọi callback tương ứng"""
        while self.running:
            try:
                pdu = self.pdu_queue.get(timeout=1.0)
                self._handle_pdu(pdu)
            except Empty:
                continue
            except Exception as e:
                if self.running:
                    self.logger(f"[ClientNetwork] Lỗi PDU loop: {e}")

    def _handle_pdu(self, pdu: dict):
        """Phân loại PDU và gọi callback cho lớp Client"""
        ptype = pdu.get("type")
        
        if ptype == "input":
            if self.on_input_pdu:
                self.on_input_pdu(pdu)
        
        elif ptype == "control":
            if self.on_control_pdu:
                self.on_control_pdu(pdu)
        
        elif ptype == "file_ack":
            if self.on_file_ack:
                self.on_file_ack(pdu)
        
        elif ptype == "file_nak":
            if self.on_file_nak:
                self.on_file_nak(pdu)
        
        elif ptype.startswith("file_"):
            if self.on_file_pdu:
                self.on_file_pdu(pdu)
        
        # Client không nhận PDU video

    def _next_seq(self):
        with self.lock:
            self.seq = (self.seq + 1) & 0xFFFFFFFF
            return self.seq

    # --- Public API cho ClientSender và Client ---

    def send_mcs_pdu(self, channel_id: int, pdu_bytes: bytes):
        if not self.running or not self.client: 
            return
        try:
            mcs_frame = MCSLite.build(channel_id, pdu_bytes)
            tpkt_packet = TPKTLayer.pack(mcs_frame)
            
            with self.lock:
                totalsent = 0
                data_to_send = tpkt_packet
                
                while totalsent < len(data_to_send):
                    sent = self.client.send(data_to_send[totalsent:])
                    if sent is None: # Sửa điều kiện kiểm tra
                        raise ConnectionError("Socket broken")
                    if sent == 0: 
                        # Socket đang bận/đầy, không nên throw error ngay
                        # Chờ xíu rồi thử lại hoặc return để ClientSender gửi lại sau
                        time.sleep(0.01)
                        continue
                    totalsent += sent

        except (socket.timeout, BlockingIOError):
            # [SỬA] Đừng ngắt kết nối khi Timeout, chỉ in log và bỏ qua gói này
            # Video frame sau sẽ bù đắp lại
            self.logger(f"[ClientNetwork] Socket Busy/Timeout. Bỏ qua gói tin.")
            return 

        except (ssl.SSLError, ConnectionError) as e:
            self.logger(f"[ClientNetwork] Lỗi kết nối nghiêm trọng: {e}")
            self._on_receiver_done() # Chỉ ngắt khi lỗi thực sự nghiêm trọng
            
        except Exception as e:
            self.logger(f"[ClientNetwork] Lỗi gửi PDU: {e}")
            # Có thể không cần ngắt kết nối ở đây tùy vào mức độ lỗi

    def send_cursor_pdu(self, x_norm: float, y_norm: float, cursor_shape_bytes: bytes = None):
        """Gửi PDU Cursor tới Server (dùng để chuyển tiếp tới Manager)"""
        seq = self._next_seq()
        
        # PDUBuilder.build_cursor_pdu: Cần có ở common_network/pdu_builder.py
        pdu = self.builder.build_cursor_pdu(
            seq, 
            int(x_norm * 10000), # Gửi dưới dạng giá trị chuẩn hóa (0-10000)
            int(y_norm * 10000), # Sẽ được Client/Manager tự decode
            cursor_shape_bytes
        )
        self.send_mcs_pdu(CHANNEL_CURSOR, pdu)

    def send_control_pdu(self, message: str):
        """Gửi một PDU Control tới server"""
        seq = self._next_seq()
        pdu = self.builder.build_control_pdu(seq, message.encode())
        self.send_mcs_pdu(CHANNEL_CONTROL, pdu)

    def register(self):
        """Đăng ký với server là 'client'"""
        self.logger(f"[ClientNetwork] Đăng ký với server với ID: {self.client_id}...")
        self.send_control_pdu(CMD_REGISTER)