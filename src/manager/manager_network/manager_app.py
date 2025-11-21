# manager/manager_network/manager_app.py

import threading
import json
from queue import Queue, Empty
from .manager_client import ManagerClient
from .manager_receiver import ManagerReceiver
from common_network.pdu_builder import PDUBuilder
from common_network.mcs_layer import MCSLite
from common_network.tpkt_layer import TPKTLayer
from manager.manager_constants import (
    CHANNEL_CONTROL, CHANNEL_INPUT,
    CMD_REGISTER, CMD_LIST_CLIENTS, CMD_CONNECT_CLIENT, CMD_DISCONNECT,
    CMD_CLIENT_LIST_UPDATE, CMD_SESSION_STARTED, CMD_SESSION_ENDED, CMD_ERROR
)

class ManagerApp:
    def __init__(self, host: str, port: int, manager_id: str = "manager1"):
        self.client = ManagerClient(host, port, manager_id)
        self.receiver = None
        self.running = False
        
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
            if msg.startswith(CMD_CLIENT_LIST_UPDATE):
                if self.on_client_list_update:
                    try:
                        client_list = json.loads(msg.split(":", 1)[1])
                        self.on_client_list_update(client_list)
                    except Exception as e:
                        print(f"Lỗi parse client list: {e}")
            elif msg.startswith(CMD_SESSION_STARTED):
                if self.on_session_started:
                    self.on_session_started(msg.split(":", 1)[1])
            elif msg.startswith(CMD_SESSION_ENDED):
                if self.on_session_ended:
                    self.on_session_ended(msg.split(":", 1)[1])
            elif msg.startswith(CMD_ERROR):
                if self.on_error:
                    self.on_error(msg.split(":", 1)[1])
            elif self.on_control_pdu:
                self.on_control_pdu(pdu)

        elif ptype in ("full", "rect"):
            if self.on_video_pdu:
                self.on_video_pdu(pdu)

        elif ptype == "cursor": 
            if self.on_cursor_pdu:
                self.on_cursor_pdu(pdu)

        elif ptype.startswith("file_"):
            if self.on_file_pdu:
                self.on_file_pdu(pdu)

    def _next_seq(self):
        with self.lock:
            self.seq = (self.seq + 1) & 0xFFFFFFFF
            return self.seq

    def _send_mcs_pdu(self, channel_id: int, pdu_bytes: bytes):
        if not self.running or not self.client.sock:
            return
        try:
            mcs_frame = MCSLite.build(channel_id, pdu_bytes)
            tpkt_packet = TPKTLayer.pack(mcs_frame)
            with self.lock:
                self.client.sock.sendall(tpkt_packet)
        except Exception as e:
            print(f"[ManagerApp] Lỗi gửi PDU: {e}")
            self._on_receiver_done()

    def _send_control_pdu(self, message: str):
        seq = self._next_seq()
        pdu = self.builder.build_control_pdu(seq, message.encode())
        self._send_mcs_pdu(CHANNEL_CONTROL, pdu)

    def register(self):
        print("[ManagerApp] Đăng ký với server...")
        self._send_control_pdu(CMD_REGISTER)

    def request_client_list(self):
        self._send_control_pdu(CMD_LIST_CLIENTS)

    def connect_to_client(self, client_id: str):
        print(f"[ManagerApp] Yêu cầu kết nối tới {client_id}...")
        self._send_control_pdu(f"{CMD_CONNECT_CLIENT}{client_id}")

    def disconnect_session(self):
        print("[ManagerApp] Yêu cầu ngắt kết nối phiên...")
        self._send_control_pdu(CMD_DISCONNECT)

    def send_input(self, event: dict):
        seq = self._next_seq()
        pdu = self.builder.build_input_pdu(seq, event)
        self._send_mcs_pdu(CHANNEL_INPUT, pdu)