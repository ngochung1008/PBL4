# manager/manager_network/manager_app.py

import threading
import json
from queue import Queue, Empty
from .manager_client import ManagerClient
from .manager_receiver import ManagerReceiver
from src.common.network.pdu_builder import PDUBuilder
from src.common.network.mcs_layer import MCSLite
from src.common.network.tpkt_layer import TPKTLayer
from src.manager.manager_constants import (
    CHANNEL_CONTROL, CHANNEL_INPUT,
    CMD_REGISTER, CMD_LOGIN, CMD_LIST_CLIENTS, CMD_VIEW_CLIENT, CMD_CONTROL_CLIENT, 
    CMD_STOP_VIEW, CMD_STOP_CONTROL, CMD_DISCONNECT,
    CMD_CLIENT_LIST_UPDATE, CMD_SESSION_STARTED, CMD_SESSION_ENDED, 
    CMD_VIEW_STARTED, CMD_CONTROL_STARTED, CMD_VIEW_ENDED, CMD_CONTROL_ENDED,
    CMD_ERROR
)

class ManagerApp:
    def __init__(self, host: str, port: int, manager_id: str = "manager1", username: str = None, password: str = None):
        self.client = ManagerClient(host, port, manager_id)
        self.receiver = None
        self.running = False
        
        self.username = username
        self.password = password
        
        self.pdu_queue = Queue()
        self.pdu_loop_thread = None
        
        self.builder = PDUBuilder()
        self.seq = 0
        self.lock = threading.Lock() 

        self.on_connected = None
        self.on_disconnected = None
        self.on_client_list_update = None
        self.on_session_started = None
        self.on_session_ended = None
        self.on_error = None
        self.on_video_pdu = None
        self.on_file_pdu = None
        self.on_control_pdu = None
        self.on_cursor_pdu = None
        self.on_input_pdu = None

    def start(self, cafile: str) -> bool:
        if not self.client.connect(cafile):
            print("[ManagerApp] Kết nối thất bại")
            return False
        
        self.running = True
        self.receiver = ManagerReceiver(self.client.sock, self.pdu_queue, self._on_receiver_done)
        self.receiver.start()
        
        self.pdu_loop_thread = threading.Thread(target=self._pdu_loop, daemon=True)
        self.pdu_loop_thread.start()
        
        print("[ManagerApp] Receiver đã khởi động.")
        self.register()
        
        if self.on_connected:
            self.on_connected()
        return True

    def stop(self):
        self.running = False
        if self.receiver:
            self.receiver.stop()
        self.client.close()
        
        with self.pdu_queue.mutex:
            self.pdu_queue.queue.clear()
            
        print("[ManagerApp] Đã dừng.")
        if self.on_disconnected:
            self.on_disconnected()
            
    def _on_receiver_done(self):
        if self.running:
            print("[ManagerApp] Mất kết nối tới server.")
            self.stop()

    def _pdu_loop(self):
        while self.running:
            try:
                pdu = self.pdu_queue.get(timeout=1.0)
                self._handle_pdu(pdu)
            except Empty:
                continue
            except Exception as e:
                if self.running:
                    print(f"[ManagerApp] Lỗi PDU loop: {e}")

    def _handle_pdu(self, pdu: dict):
        """Phân loại PDU và gọi callback cho UI"""
        ptype = pdu.get("type")
        
        if ptype == "control":
            msg = pdu.get("message", "")
            print(f"[ManagerApp] Nhận CONTROL PDU: {msg[:100]}...")  # DEBUG
            if msg.startswith(CMD_CLIENT_LIST_UPDATE):
                if self.on_client_list_update:
                    try:
                        client_list_json = msg.split(":", 1)[1]
                        print(f"[ManagerApp] Parsing client list JSON: {client_list_json}")  # DEBUG
                        client_list = json.loads(client_list_json)
                        print(f"[ManagerApp] ✅ Received client list: {client_list}")  # DEBUG
                        self.on_client_list_update(client_list)
                    except Exception as e:
                        print(f"[ManagerApp] ❌ Lỗi parse client list: {e}")
                        import traceback
                        traceback.print_exc()
            elif msg.startswith(CMD_SESSION_STARTED):
                if self.on_session_started:
                    self.on_session_started(msg.split(":", 1)[1])
            elif msg.startswith(CMD_VIEW_STARTED):
                # New: VIEW session started
                if self.on_session_started:
                    self.on_session_started(msg.split(":", 1)[1])
            elif msg.startswith(CMD_CONTROL_STARTED):
                # New: CONTROL session started
                if self.on_session_started:
                    self.on_session_started(msg.split(":", 1)[1])
            elif msg.startswith(CMD_SESSION_ENDED):
                if self.on_session_ended:
                    self.on_session_ended(msg.split(":", 1)[1])
            elif msg.startswith(CMD_VIEW_ENDED):
                # New: VIEW session ended
                if self.on_session_ended:
                    self.on_session_ended(msg.split(":", 1)[1])
            elif msg.startswith(CMD_CONTROL_ENDED):
                # New: CONTROL session ended
                if self.on_session_ended:
                    self.on_session_ended(msg.split(":", 1)[1])
            elif msg.startswith(CMD_ERROR):
                if self.on_error:
                    self.on_error(msg.split(":", 1)[1])
            elif self.on_control_pdu:
                self.on_control_pdu(pdu)

        elif ptype in ("full", "rect"):
            print(f"[ManagerApp] Xử lý VIDEO PDU: {ptype}")
            if self.on_video_pdu:
                self.on_video_pdu(pdu)
            else:
                print(f"[ManagerApp] ⚠️ CẢNH BÁO: on_video_pdu callback CHƯA được đăng ký!")

        elif ptype == "cursor": 
            if self.on_cursor_pdu:
                self.on_cursor_pdu(pdu)

        elif ptype == "input":
            if self.on_input_pdu:
                self.on_input_pdu(pdu)
                
        elif ptype == "file":
            # File data PDU
            if self.on_file_pdu:
                self.on_file_pdu(pdu)
        
        elif ptype.startswith("file_"):
            if self.on_file_pdu:
                self.on_file_pdu(pdu)

    def _next_seq(self):
        with self.lock:
            self.seq = (self.seq + 1) & 0xFFFFFFFF
            return self.seq

    def _send_mcs_pdu(self, channel_id: int, pdu_bytes: bytes):
        if not self.running:
            print(f"[ManagerApp] ⚠️ Cannot send PDU - not running (channel={channel_id})")
            return
        if not self.client.sock:
            print(f"[ManagerApp] ⚠️ Cannot send PDU - socket is None (channel={channel_id})")
            return
        try:
            mcs_frame = MCSLite.build(channel_id, pdu_bytes)
            tpkt_packet = TPKTLayer.pack(mcs_frame)
            with self.lock:
                self.client.sock.sendall(tpkt_packet)
            # Debug log for file transfers
            if channel_id == 5:  # CHANNEL_FILE
                print(f"[ManagerApp] 📤 Sent FILE PDU: {len(pdu_bytes)} bytes")
        except Exception as e:
            print(f"[ManagerApp] Lỗi gửi PDU: {e}")
            import traceback
            traceback.print_exc()
            self._on_receiver_done()

    def _send_control_pdu(self, message: str):
        seq = self._next_seq()
        pdu = self.builder.build_control_pdu(seq, message.encode())
        self._send_mcs_pdu(CHANNEL_CONTROL, pdu)

    def register(self):
        print("[ManagerApp] Đăng ký với server...")
        if self.username and self.password:
            self._send_control_pdu(f"{CMD_LOGIN}{self.username}:{self.password}:manager")
        else:
            self._send_control_pdu(f"{CMD_REGISTER}manager")

    def request_client_list(self):
        self._send_control_pdu(CMD_LIST_CLIENTS)

    def connect_to_client(self, client_id: str, mode: str = "control"):
        """Legacy method - deprecated"""
        print(f"[ManagerApp] connect_to_client (DEPRECATED) - use view_client or control_client")
        self.control_client(client_id)
    
    def view_client(self, client_id: str):
        """Gửi yêu cầu VIEW client (chỉ xem)"""
        print(f"[ManagerApp] 👁️ Yêu cầu VIEW tới {client_id}...")
        self._send_control_pdu(f"{CMD_VIEW_CLIENT}{client_id}")
    
    def control_client(self, client_id: str):
        """Gửi yêu cầu CONTROL client (xem và điều khiển)"""
        print(f"[ManagerApp] 🎮 Yêu cầu CONTROL tới {client_id}...")
        self._send_control_pdu(f"{CMD_CONTROL_CLIENT}{client_id}")
    
    def stop_view(self):
        """Dừng VIEW session"""
        print(f"[ManagerApp] Yêu cầu dừng VIEW session...")
        self._send_control_pdu(CMD_STOP_VIEW)
    
    def stop_control(self):
        """Dừng CONTROL session"""
        print(f"[ManagerApp] Yêu cầu dừng CONTROL session...")
        self._send_control_pdu(CMD_STOP_CONTROL)

    def disconnect_session(self, mode: str = "control"):
        """Legacy method - deprecated"""
        print(f"[ManagerApp] disconnect_session (DEPRECATED) - use stop_view or stop_control")
        self.stop_control()

    def send_input(self, event: dict):
        print(f"[ManagerApp] 📤 Gửi input event: {event.get('type')}")
        seq = self._next_seq()
        pdu = self.builder.build_input_pdu(seq, event)
        print(f"[ManagerApp] PDU được build: seq={seq}, size={len(pdu)} bytes")
        self._send_mcs_pdu(CHANNEL_INPUT, pdu)
    def send_control_message(self, message: str):
        """G?i control message t?i server"""
        print(f"[ManagerApp] ?? G?i control message: {message[:100]}")
        self._send_control_pdu(message)
    
    def next_seq(self):
        """Public method d? l?y sequence number"""
        return self._next_seq()
