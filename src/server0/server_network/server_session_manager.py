import threading
import json
import time
from queue import Queue, Empty
from server0.server_network.server_session import ServerSession
from server0.server_constants import (
    ROLE_MANAGER, ROLE_CLIENT, ROLE_UNKNOWN,
    CMD_REGISTER, CMD_LIST_CLIENTS, CMD_CONNECT_CLIENT, CMD_DISCONNECT,
    CMD_REGISTER_OK, CMD_CLIENT_LIST_UPDATE, CMD_SESSION_STARTED, CMD_SESSION_ENDED,
    CMD_ERROR, CHANNEL_CONTROL
)
from common_network.pdu_builder import PDUBuilder
from common_network.mcs_layer import MCSLite

class SessionManager(threading.Thread):
    """
    Quản lý việc đăng ký (client/manager) và các phiên (session) đang hoạt động.
    """
    def __init__(self, broadcaster):
        super().__init__(daemon=True, name="SessionManager")
        self.broadcaster = broadcaster
        self.pdu_queue = Queue() # Queue nội bộ để xử lý PDU đăng ký
        self.running = True
        
        self.builder = PDUBuilder()
        self.seq = 0 # Bộ đếm sequence cho tin nhắn từ server
        
        # { cid -> role }
        self.clients = {} 
        # { cid -> session }
        self.client_session_map = {}
        # { session_id -> session_thread }
        self.active_sessions = {}
        
        self.lock = threading.Lock()

    def start(self):
        self.running = True
        super().start()
        print("[SessionManager] Đã khởi động.")

    def stop(self):
        self.running = False
        print("[SessionManager] Đang dừng...")
        with self.lock:
            sessions = list(self.active_sessions.values())
        
        print(f"[SessionManager] Dừng {len(sessions)} phiên đang hoạt động...")
        for s in sessions:
            s.stop()
        
        with self.pdu_queue.mutex:
            self.pdu_queue.queue.clear()
        print("[SessionManager] Đã dừng.")

    # --- Callbacks từ ServerNetwork ---

    def handle_new_connection(self, client_id, ssl_sock):
        """Được gọi bởi ServerNetwork khi có kết nối mới"""
        with self.lock:
            self.clients[client_id] = ROLE_UNKNOWN
        print(f"[SessionManager] Client {client_id} đã kết nối (chưa rõ vai trò).")

    def handle_disconnection(self, client_id):
        """Được gọi bởi ServerNetwork khi client mất kết nối"""
        print(f"[SessionManager] Client {client_id} đã ngắt kết nối.")
        session = None
        role = ROLE_UNKNOWN
        with self.lock:
            role = self.clients.pop(client_id, ROLE_UNKNOWN)
            # Nếu client này đang trong 1 phiên, kết thúc phiên đó
            session = self.client_session_map.pop(client_id, None)
            
        if session:
            print(f"[SessionManager] Dừng phiên {session.session_id} do {client_id} ngắt kết nối.")
            session.stop()
            with self.lock:
                self.active_sessions.pop(session.session_id, None)
                # Báo cho bên còn lại biết phiên đã kết thúc
                other_party_id = session.manager_id if client_id == session.client_id else session.client_id
                self.client_session_map.pop(other_party_id, None)
                self._send_control_pdu(other_party_id, f"{CMD_SESSION_ENDED}:{client_id}")

        if role == ROLE_CLIENT:
            # Nếu là client, cập nhật danh sách cho tất cả manager
            self._broadcast_client_list()

    def handle_pdu(self, client_id, pdu):
        """
        Được gọi bởi ServerNetwork khi có PDU mới.
        Kiểm tra PDU:
        - Nếu là PDU điều khiển (register, connect), xử lý ngay.
        - Nếu là PDU trong phiên (input, video), chuyển cho ServerSession tương ứng.
        """
        session = None
        with self.lock:
            session = self.client_session_map.get(client_id)
            
        if session:
            # Client này đang trong 1 phiên, chuyển PDU cho luồng của phiên đó
            session.enqueue_pdu(client_id, pdu)
        else:
            # Client chưa có phiên, PDU này phải là PDU điều khiển (register/connect)
            # Đưa vào queue nội bộ của SessionManager để xử lý
            self.pdu_queue.put((client_id, pdu))

    # --- Vòng lặp xử lý chính ---

    def run(self):
        """Xử lý PDU điều khiển (register, connect, ...)"""
        while self.running:
            try:
                client_id, pdu = self.pdu_queue.get(timeout=0.5)
                ptype = pdu.get("type")
                
                # Chỉ xử lý PDU CONTROL khi chưa vào phiên
                if ptype == "control":
                    self._handle_control_pdu(client_id, pdu)
                    
            except Empty:
                continue
            except Exception as e:
                print(f"[SessionManager] Lỗi xử lý PDU: {e}")

    def _handle_control_pdu(self, client_id, pdu):
        """Xử lý PDU điều khiển từ client/manager chưa có phiên"""
        msg = pdu.get("message", "")
        
        # --- Xử lý Đăng ký ---
        if msg.startswith(CMD_REGISTER):
            role = msg.split(":", 1)[1].strip()
            if role in (ROLE_MANAGER, ROLE_CLIENT):
                with self.lock:
                    self.clients[client_id] = role
                print(f"[SessionManager] {client_id} đăng ký vai trò: {role}")
                self._send_control_pdu(client_id, f"{CMD_REGISTER_OK}:{role}")
                
                if role == ROLE_CLIENT:
                    self._broadcast_client_list() # Cập nhật cho manager
                elif role == ROLE_MANAGER:
                    self._send_client_list(client_id) # Gửi danh sách cho manager mới
            else:
                self._send_control_pdu(client_id, f"{CMD_ERROR}:Vai trò không hợp lệ")

        # --- Xử lý Yêu cầu danh sách Client ---
        elif msg == CMD_LIST_CLIENTS:
            if self.clients.get(client_id) == ROLE_MANAGER:
                self._send_client_list(client_id)
        
        # --- Xử lý Yêu cầu Kết nối ---
        elif msg.startswith(CMD_CONNECT_CLIENT):
            if self.clients.get(client_id) != ROLE_MANAGER:
                self._send_control_pdu(client_id, f"{CMD_ERROR}:Chỉ manager mới được kết nối")
                return

            target_cid = msg.split(":", 1)[1].strip()
            self._start_new_session(client_id, target_cid)

    # --- Quản lý Phiên (Session) ---

    def _start_new_session(self, manager_id, client_id):
        with self.lock:
            if self.client_session_map.get(manager_id):
                self._send_control_pdu(manager_id, f"{CMD_ERROR}:Bạn đã ở trong 1 phiên")
                return
            if self.client_session_map.get(client_id):
                self._send_control_pdu(manager_id, f"{CMD_ERROR}:Client {client_id} đang bận")
                return
            if self.clients.get(client_id) != ROLE_CLIENT:
                self._send_control_pdu(manager_id, f"{CMD_ERROR}:Client {client_id} không tồn tại")
                return
        
        print(f"[SessionManager] Bắt đầu phiên mới: {manager_id} <-> {client_id}")
        session = ServerSession(manager_id, client_id, self.broadcaster, self._on_session_done)
        session.start()
        
        with self.lock:
            self.active_sessions[session.session_id] = session
            self.client_session_map[manager_id] = session
            self.client_session_map[client_id] = session
            
        # Thông báo cho cả 2 bên
        self._send_control_pdu(manager_id, f"{CMD_SESSION_STARTED}:{client_id}")
        self._send_control_pdu(client_id, f"{CMD_SESSION_STARTED}:{manager_id}")

    def _on_session_done(self, session, reason):
        """Callback được gọi bởi ServerSession khi nó kết thúc"""
        print(f"[SessionManager] Phiên {session.session_id} kết thúc. Lý do: {reason}")
        with self.lock:
            self.active_sessions.pop(session.session_id, None)
            self.client_session_map.pop(session.manager_id, None)
            self.client_session_map.pop(session.client_id, None)
            
        # Báo cho 2 bên (nếu họ vẫn còn kết nối)
        if self.clients.get(session.manager_id):
             self._send_control_pdu(session.manager_id, f"{CMD_SESSION_ENDED}:{session.client_id}")
        if self.clients.get(session.client_id):
             self._send_control_pdu(session.client_id, f"{CMD_SESSION_ENDED}:{session.manager_id}")


    # --- Gửi tin nhắn Tiện ích ---

    def _get_available_clients(self):
        """Lấy danh sách client đang rảnh (thread-safe)"""
        available = []
        with self.lock:
            for cid, role in self.clients.items():
                if role == ROLE_CLIENT and cid not in self.client_session_map:
                    available.append(cid)
        return available

    def _send_client_list(self, manager_id):
        """Gửi danh sách client rảnh cho 1 manager"""
        clients = self._get_available_clients()
        msg = f"{CMD_CLIENT_LIST_UPDATE}:{json.dumps(clients)}"
        self._send_control_pdu(manager_id, msg)
        
    def _broadcast_client_list(self):
        """Gửi danh sách client rảnh cho TẤT CẢ manager rảnh"""
        clients = self._get_available_clients()
        msg = f"{CMD_CLIENT_LIST_UPDATE}:{json.dumps(clients)}"
        
        managers_to_notify = []
        with self.lock:
            for cid, role in self.clients.items():
                if role == ROLE_MANAGER and cid not in self.client_session_map:
                    managers_to_notify.append(cid)
                    
        for mid in managers_to_notify:
            self._send_control_pdu(mid, msg)

    def _send_control_pdu(self, target_id, message: str):
        """Gửi 1 PDU CONTROL tới client/manager"""
        if not self.broadcaster: return
        
        with self.lock:
            self.seq += 1
            pdu_bytes = self.builder.build_control_pdu(self.seq, message.encode())
        
        mcs_frame = MCSLite.build(CHANNEL_CONTROL, pdu_bytes)
        self.broadcaster.enqueue(target_id, mcs_frame)