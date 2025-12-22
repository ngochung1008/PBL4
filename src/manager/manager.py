# manager/manager.py

import sys
import time
import os
from PIL import Image
import io
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, pyqtSignal

# Lấy đường dẫn tuyệt đối của file manager.py hiện tại
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))

# Thêm đường dẫn gốc vào sys.path để Python nhìn thấy module 'src'
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.manager.manager_network.manager_app import ManagerApp
from src.manager.gui.manager_gui import ManagerWindow 
from src.manager.manager_input import ManagerInputHandler
from src.manager.manager_viewer import ManagerViewer
from src.manager.manager_constants import CA_FILE
from src.manager.manager_file_transfer import ManagerFileTransfer

class Manager(QObject): 
    
    client_list_updated = pyqtSignal(list)
    session_started = pyqtSignal(str)
    session_ended = pyqtSignal()
    video_pdu_received = pyqtSignal(object) 
    error_received = pyqtSignal(str)
    disconnected_from_server = pyqtSignal()
    cursor_pdu_received = pyqtSignal(object)
    input_pdu_received = pyqtSignal(object)  # Keylog data
    security_alert_received = pyqtSignal(object)  # Security alerts
    file_received = pyqtSignal(str, str, str)  # filename, filepath, sender_id
    file_send_progress = pyqtSignal(int)  # progress percentage
    file_send_complete = pyqtSignal(str)  # filename
    file_send_error = pyqtSignal(str)  # error message

    def __init__(self, host: str, port: int, manager_id: str = "manager1", username: str = None, password: str = None):
        super().__init__()
        
        self.app = ManagerApp(host, port, manager_id, username, password)
        self.input_handler = ManagerInputHandler(self.app)
        self.viewer = ManagerViewer()
        
        # File Transfer
        self.file_transfer = ManagerFileTransfer(self.app)
        
        # Buffer để nhận file chunks
        self.receiving_chunks = []
        self.receiving_total_size = 0
        self._setup_file_transfer_callbacks()
        
        self.current_session_client_id = None
        self.client_list = []

        self.app.on_connected = self._on_connected
        self.app.on_disconnected = self._on_disconnected
        self.app.on_client_list_update = self._on_client_list_update
        self.app.on_session_started = self._on_session_started
        self.app.on_session_ended = self._on_session_ended
        self.app.on_error = self._on_error
        self.app.on_video_pdu = self._on_video_pdu
        self.app.on_file_pdu = self._on_file_pdu
        self.app.on_control_pdu = self._on_control_pdu
        self.app.on_cursor_pdu = self._on_cursor_pdu
        self.app.on_input_pdu = self._on_input_pdu

    def start(self):
        if not os.path.exists(CA_FILE):
            print(f"Lỗi: Không tìm thấy file CA: '{CA_FILE}'")
            return False
        
        print("[Manager] Đang khởi động...")
        ok = self.app.start(cafile=CA_FILE)
        if not ok:
            print("[Manager] Khởi động thất bại.")
            return False
        
        print("[Manager] Đã khởi động và đăng ký với server.")
        
        # Request client list ngay sau khi kết nối
        import time
        time.sleep(0.5)  # Đợi registration hoàn tất
        print("[Manager] Yêu cầu danh sách client từ server...")
        self.app.request_client_list()
        
        return True

    def stop(self):
        print("[Manager] Đang dừng...")
        self.app.stop()
        print("[Manager] Đã dừng.")

    # --- Các hàm xử lý Callback (Giữ nguyên) ---

    def _on_connected(self):
        print("[Manager] Đã kết nối tới server.")

    def _on_disconnected(self):
        print("[Manager] Mất kết nối tới server.")
        self.current_session_client_id = None
        self.client_list = []
        self.disconnected_from_server.emit()

    def _on_client_list_update(self, client_list: list):
        self.client_list = client_list
        print(f"[Manager] ✅ Danh sách client rảnh từ server: {self.client_list}")
        print(f"[Manager] Client IDs: {[c['id'] for c in client_list]}")
        self.client_list_updated.emit(client_list)

    def _on_session_started(self, client_id: str):
        # Server xác nhận session đã bắt đầu
        if self.current_session_client_id != client_id:
            print(f"[WARN] Server xác nhận ID {client_id} khác với ID dự kiến {self.current_session_client_id}")
            self.current_session_client_id = client_id
            
        print(f"[Manager] Phiên làm việc với '{client_id}' đã CHÍNH THỨC bắt đầu.")
        self.session_started.emit(client_id)

    def _on_session_ended(self, client_id: str):
        print(f"[Manager] ⚠️ Phiên làm việc với '{client_id}' đã kết thúc (từ server).")
        print(f"[Manager] Session kết thúc: current_session_client_id = {self.current_session_client_id}")
        
        # Luôn reset, không cần check
        self.current_session_client_id = None
        print(f"[Manager] Đã reset current_session_client_id = None")
        
        # Emit signal
        self.session_ended.emit()
        
        # Request client list để cập nhật danh sách
        self.app.request_client_list()

    def _on_error(self, error_msg: str):
        print(f"[Manager] Lỗi từ Server: {error_msg}")
        self.error_received.emit(error_msg)

    def _on_video_pdu(self, pdu: dict):
        if not self.current_session_client_id:
            # Nếu chạy vào đây nghĩa là Lỗi Race Condition vẫn còn
            print(f"[Manager] CẢNH BÁO: Bỏ qua video PDU vì chưa có Session ID! Type: {pdu.get('type')}")
            return
        
        print(f"[Manager] Đang xử lý video PDU: {pdu.get('type')} cho client: {self.current_session_client_id}")
        try:
            updated_img = self.viewer.process_video_pdu(self.current_session_client_id, pdu)
            
            if updated_img:
                print(f"[Manager] ✅ Đã xử lý và emit video frame, size: {updated_img.size}")
                self.video_pdu_received.emit(updated_img)
            else:
                print(f"[Manager] ⚠️ process_video_pdu trả về None")
        except Exception as e:
            print(f"[Manager] LỖI khi xử lý video PDU: {e}")
            import traceback
            traceback.print_exc()
        
    def _on_file_pdu(self, pdu: dict):
        """Xử lý file PDU từ server"""
        try:
            import struct
            import json
            
            pdu_type = pdu.get('type')
            print(f"[Manager] ===== Received FILE PDU =====")
            print(f"[Manager] PDU type: {pdu_type}")
            
            # Xử lý file_chunk PDU (format mới)
            if pdu_type == 'file_chunk':
                chunk_data = pdu.get('data', b'')
                offset = pdu.get('offset', 0)
                
                if chunk_data:
                    print(f"[Manager] Received chunk at offset {offset}, size: {len(chunk_data)} bytes")
                    
                    # Thêm chunk vào buffer
                    self.receiving_chunks.append((offset, chunk_data))
                    self.receiving_total_size += len(chunk_data)
                    
                    # Thử lắp ráp file
                    self._try_complete_file_from_chunks()
                return
            
            # Legacy format: raw_payload
            raw_payload = pdu.get('_raw_payload')
            if not raw_payload:
                print(f"[Manager] No raw_payload in file PDU")
                return
            
            # Extract metadata and file data
            # Format: [metadata_len(4bytes)][metadata_json][file_data]
            if len(raw_payload) < 4:
                print(f"[Manager] Invalid file PDU: too short")
                return
            
            metadata_len = struct.unpack('>I', raw_payload[:4])[0]
            metadata_bytes = raw_payload[4:4+metadata_len]
            file_data = raw_payload[4+metadata_len:]
            
            metadata = json.loads(metadata_bytes.decode('utf-8'))
            
            print(f"[Manager] Received file: {metadata.get('filename')} from {metadata.get('sender_id')}")
            
            # Pass to file transfer handler
            self.file_transfer.handle_file_received(metadata, file_data)
            
        except Exception as e:
            print(f"[Manager] Error handling file PDU: {e}")
            import traceback
            traceback.print_exc()
    
    def _try_complete_file_from_chunks(self):
        """Thử lắp ráp file từ các chunks đã nhận"""
        import struct
        import json
        
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
            
            print(f"[Manager] Parsed metadata: {metadata}")
            print(f"[Manager] Expected filesize: {expected_filesize}, received: {len(file_data)}")
            
            # Kiểm tra đã nhận đủ file chưa
            if len(file_data) >= expected_filesize:
                # Đã nhận đủ → lưu file
                print(f"[Manager] File complete! Saving...")
                
                # Lấy đúng kích thước file (không lấy padding)
                file_data = file_data[:expected_filesize]
                
                self.file_transfer.handle_file_received(metadata, file_data)
                
                # Reset buffer
                self.receiving_chunks = []
                self.receiving_total_size = 0
                
        except (struct.error, json.JSONDecodeError) as e:
            # Có thể chưa nhận đủ metadata, tiếp tục chờ
            print(f"[Manager] Waiting for more chunks... ({e})")
            pass
    
    def _setup_file_transfer_callbacks(self):
        """Setup callbacks cho file transfer"""
        self.file_transfer.on_file_received = self._on_file_received_callback
        self.file_transfer.on_file_send_progress = self._on_file_send_progress_callback
        self.file_transfer.on_file_send_complete = self._on_file_send_complete_callback
        self.file_transfer.on_file_send_error = self._on_file_send_error_callback
    
    def _on_file_received_callback(self, filename, filepath, sender_id):
        """Callback khi nhận được file"""
        print(f"[Manager] ✅ File received: {filename} from {sender_id}")
        self.file_received.emit(filename, filepath, sender_id)
    
    def _on_file_send_progress_callback(self, progress):
        """Callback cập nhật progress khi gửi file"""
        print(f"[Manager] 📤 Send progress: {progress}%")
        self.file_send_progress.emit(progress)
    
    def _on_file_send_complete_callback(self, filename):
        """Callback khi gửi file hoàn thành"""
        print(f"[Manager] ✅ File sent: {filename}")
        self.file_send_complete.emit(filename)
    
    def _on_file_send_error_callback(self, error_msg):
        """Callback khi có lỗi gửi file"""
        print(f"[Manager] ❌ Send error: {error_msg}")
        self.file_send_error.emit(error_msg)
    
    def gui_send_file(self, target_client_id: str, filepath: str):
        """Gửi file tới client"""
        print(f"[Manager] Sending file {filepath} to {target_client_id}")
        return self.file_transfer.send_file(target_client_id, filepath)
    
    def _on_control_pdu(self, pdu: dict):
        msg = pdu.get('message', '')
        print(f"[Manager] Control PDU từ client: {msg}")
        
        # Xử lý file transfer commands
        if isinstance(msg, str):
            if msg.startswith('file_transfer_start:'):
                # Server ACK - bắt đầu gửi file data
                transfer_id = msg.split(':', 1)[1]
                print(f"[Manager] 📤 Received file_transfer_start, sending file data...")
                self.file_transfer.handle_file_transfer_ack(transfer_id)
            
            elif msg.startswith('file_transfer_ack:'):
                # Progress update
                parts = msg.split(':')
                if len(parts) >= 3:
                    transfer_id = parts[1]
                    progress = int(parts[2])
                    self.file_send_progress.emit(progress)
            
            elif msg.startswith('file_transfer_complete:'):
                # Transfer completed
                parts = msg.split(':', 2)
                if len(parts) >= 3:
                    transfer_id = parts[1]
                    filename = parts[2]
                    self.file_transfer.handle_transfer_complete(transfer_id, filename)
            
            elif msg.startswith('file_transfer_error:'):
                # Transfer error
                error = msg.split(':', 1)[1] if ':' in msg else 'Unknown error'
                self.file_transfer.handle_transfer_error(error)
            
            # Kiểm tra xem có phải là security alert không
            elif msg.startswith('security_alert:'):
                print(f"[Manager] 🚨 Nhận được security alert: {msg}")
                self.security_alert_received.emit(pdu)
        
        elif isinstance(msg, bytes) and msg.startswith(b'security_alert:'):
            # Decode bytes nếu cần
            pdu['message'] = msg.decode('utf-8')
            print(f"[Manager] 🚨 Nhận được security alert (decoded): {pdu['message']}")
            self.security_alert_received.emit(pdu)
    
    def _on_input_pdu(self, pdu: dict):
        """Xử lý INPUT PDU (keylog data) từ client - LUÔN LUÔN nhận, không cần session"""
        # KHÔNG kiểm tra session nữa - keylog luôn được nhận
        message = pdu.get('message', '')
        print(f"[Manager] 📝 Keylog từ client: {message[:50]}...")  # Log 50 ký tự đầu
        print(f"[Manager] 🔔 Emitting input_pdu_received signal with pdu={pdu}")
        self.input_pdu_received.emit(pdu)
        print(f"[Manager] ✅ Signal emitted")

    # --- Slots (Hàm được gọi từ GUI) (Giữ nguyên) ---

    def _on_cursor_pdu(self, pdu: dict):
        if not self.current_session_client_id:
            return
        # pdu chứa x, y (đã chuẩn hóa), cursor_shape (bytes)
        self.cursor_pdu_received.emit(pdu) # Gửi thẳng dict PDU lên GUI/Viewer

    def gui_connect_to_client(self, client_id: str):
        """Legacy method - deprecated, use gui_view_client or gui_control_client instead"""
        print(f"[Manager] gui_connect_to_client (DEPRECATED) được gọi với client_id: {client_id}")
        # Fallback to view mode
        self.gui_view_client(client_id)
    
    def gui_view_client(self, client_id: str):
        """Gửi yêu cầu VIEW client (chỉ xem màn hình, không điều khiển)"""
        print(f"[Manager] 👁️ gui_view_client được gọi với client_id: {client_id}")
        
        # Kiểm tra client_id có trong danh sách không
        client_ids = [c['id'] for c in self.client_list]
        print(f"[Manager] Danh sách client IDs hiện tại: {client_ids}")
        
        if client_id not in client_ids:
            print(f"[Manager] Client {client_id} chưa trong danh sách. Vẫn thử kết nối...")
        
        # Gán ID ngay lập tức để nhận video frame
        print(f"[Manager] Đặt session ID dự kiến: {client_id}")
        self.current_session_client_id = client_id 
        
        print(f"[Manager] Đang gửi yêu cầu VIEW tới client: {client_id}")
        self.app.view_client(client_id)
    
    def gui_control_client(self, client_id: str):
        """Gửi yêu cầu CONTROL client (xem và điều khiển)"""
        print(f"[Manager] 🎮 gui_control_client được gọi với client_id: {client_id}")
        
        # Kiểm tra client_id có trong danh sách không
        client_ids = [c['id'] for c in self.client_list]
        print(f"[Manager] Danh sách client IDs hiện tại: {client_ids}")
        
        if client_id not in client_ids:
            print(f"[Manager] Client {client_id} chưa trong danh sách. Vẫn thử kết nối...")
        
        # Gán ID ngay lập tức để nhận video frame
        print(f"[Manager] Đặt session ID dự kiến: {client_id}")
        self.current_session_client_id = client_id 
        
        print(f"[Manager] Đang gửi yêu cầu CONTROL tới client: {client_id}")
        self.app.control_client(client_id)
    
    def gui_stop_view(self):
        """Dừng VIEW session"""
        print(f"[Manager] Dừng VIEW session")
        
        # Reset session ID
        self.current_session_client_id = None
        
        # Gửi stop_view request
        try:
            self.app.stop_view()
            print(f"[Manager] Đã gửi yêu cầu stop_view tới server")
        except Exception as e:
            print(f"[Manager] Lỗi khi gửi stop_view request: {e}")
        
        # Emit signal
        self.session_ended.emit()
        print(f"[Manager] ✅ Stop view hoàn tất")
    
    def gui_stop_control(self):
        """Dừng CONTROL session"""
        print(f"[Manager] Dừng CONTROL session")
        
        # Reset session ID
        self.current_session_client_id = None
        
        # Gửi stop_control request
        try:
            self.app.stop_control()
            print(f"[Manager] Đã gửi yêu cầu stop_control tới server")
        except Exception as e:
            print(f"[Manager] Lỗi khi gửi stop_control request: {e}")
        
        # Emit signal
        self.session_ended.emit()
        print(f"[Manager] ✅ Stop control hoàn tất")

    def gui_disconnect_session(self):
        client_id = self.current_session_client_id
        if not client_id:
            print("[Manager] Không có phiên đang hoạt động (có thể đã tự động disconnect).")
            return
        
        print(f"[Manager] Ngắt kết nối phiên với {client_id}...")
        
        # Reset session ID NGAY LẬP TỨC để không nhận video frame nữa
        self.current_session_client_id = None
        print(f"[Manager] Đã reset current_session_client_id = None")
        
        # Gửi yêu cầu disconnect tới server
        try:
            self.app.disconnect_session()
            print(f"[Manager] Đã gửi yêu cầu disconnect tới server")
        except Exception as e:
            print(f"[Manager] Lỗi khi gửi disconnect request: {e}")
        
        # Request lại client list để cập nhật
        try:
            self.app.request_client_list()
            print(f"[Manager] Đã request client list")
        except Exception as e:
            print(f"[Manager] Lỗi khi request client list: {e}")
        
        # Emit signal
        self.session_ended.emit()
        print(f"[Manager] ✅ Disconnect hoàn tất")

    # --- SỬA HÀM NÀY ---
    def send_input_event(self, event: dict):
        """GUI gọi hàm này khi có sự kiện chuột/phím"""
        print(f"[Manager] send_input_event được gọi: {event.get('type')}, current_session_client_id={self.current_session_client_id}")
        
        if not self.current_session_client_id:
            # Session đã kết thúc, không gửi input nữa
            print(f"[Manager] ⚠️ Không gửi input event - chưa có session!")
            return 
        
        print(f"[Manager] ✅ Gửi input event tới input_handler: {event}")
        # Gửi sự kiện đã được format bởi GUI
        self.input_handler.send_event(event)

    # --- THÊM HÀM NÀY ---
    def _on_gui_input(self, event_dict: dict):
        """Nhận signal từ GUI và gửi đi"""
        print(f"[Manager] 🎮 Nhận được input event từ GUI: {event_dict.get('type')}, current_session_client_id={self.current_session_client_id}")
        self.send_input_event(event_dict)

# --- ĐIỂM VÀO CHÍNH (THAY THẾ TEST LOOP CŨ) ---

if __name__ == "__main__":
    # 1. Cấu hình
    HOST = "192.168.2.193"
    PORT = 5000
    MANAGER_ID = "manager_gui_1"

    # 2. Khởi tạo QApplication
    app = QApplication(sys.argv)

    # 3. Khởi tạo GUI
    from src.manager.gui.manager_gui import LoginDialog
    login_dialog = LoginDialog()
    result = login_dialog.exec()
    if result != 1:
        sys.exit()
    
    # 4. Tạo connection để auth và lấy thông tin user (tùy chọn)
    from src.client.auth import ClientConnection
    try:
        conn = ClientConnection()
        token = conn.client_login(login_dialog.username, login_dialog.password)
        if not token:
            print("Cảnh báo: Đăng nhập auth service thất bại!")
            token = f"manager_{login_dialog.username}"
        
        # Lưu conn và token vào app để các GUI window khác sử dụng
        app.conn = conn
        app.current_user = token
        app.current_name = login_dialog.username
    except Exception as e:
        print(f"Cảnh báo: Không thể kết nối auth service: {e}")
        print("Tiếp tục chạy mà không có auth service...")
        # Tạo dummy connection để tránh lỗi AttributeError
        app.conn = None
        app.current_user = f"manager_{login_dialog.username}"
        app.current_name = login_dialog.username
    
    # [FIX] Khởi tạo client_connected trước khi tạo ManageClientsWindow
    app.client_connected = []  # Danh sách rỗng ban đầu, sẽ được update sau
    
    from src.manager.gui.manage_clients import ManageClientsWindow
    window = ManageClientsWindow()
    manager_logic = Manager(HOST, PORT, MANAGER_ID, login_dialog.username, login_dialog.password)
    
    # Lưu manager_logic vào app để GUI có thể access
    app.manager_logic = manager_logic
    
    # 5. Kết nối Logic và GUI
    manager_logic.client_list_updated.connect(window.update_client_list)
    manager_logic.session_started.connect(window.set_session_started)
    manager_logic.session_ended.connect(window.set_session_ended)
    manager_logic.video_pdu_received.connect(window.update_video_frame)
    manager_logic.cursor_pdu_received.connect(window.update_cursor_pos)
    manager_logic.error_received.connect(window.show_error)
    manager_logic.input_pdu_received.connect(window.display_keylog)
    manager_logic.security_alert_received.connect(window.display_security_alert)
    
    window.connect_requested.connect(manager_logic.gui_connect_to_client)
    window.disconnect_requested.connect(manager_logic.gui_disconnect_session)
    
    # --- THÊM: KẾT NỐI INPUT ---
    window.input_event_generated.connect(manager_logic._on_gui_input)
    
    # 6. Khởi động Logic Manager
    if not manager_logic.start():
        print("Không thể khởi động Manager. Thoát.")
        sys.exit(1)

    # 7. Hiển thị GUI
    window.show()
    
    app.aboutToQuit.connect(manager_logic.stop)
    
    sys.exit(app.exec())