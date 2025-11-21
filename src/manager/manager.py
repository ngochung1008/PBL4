# manager/manager.py

import sys
import time
from PIL import Image
import io
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, pyqtSignal

from manager.manager_network.manager_app import ManagerApp
from manager.manager_gui import ManagerWindow 
from manager.manager_input import ManagerInputHandler
from manager.manager_viewer import ManagerViewer
from manager.manager_constants import CA_FILE
import os

class Manager(QObject): 
    
    client_list_updated = pyqtSignal(list)
    session_started = pyqtSignal(str)
    session_ended = pyqtSignal()
    video_pdu_received = pyqtSignal(object) 
    error_received = pyqtSignal(str)
    disconnected_from_server = pyqtSignal()
    cursor_pdu_received = pyqtSignal(object)

    def __init__(self, host: str, port: int, manager_id: str = "manager1"):
        super().__init__()
        
        self.app = ManagerApp(host, port, manager_id)
        self.input_handler = ManagerInputHandler(self.app)
        self.viewer = ManagerViewer()
        
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
        print(f"[Manager] Danh sách client rảnh: {self.client_list}")
        self.client_list_updated.emit(client_list)

    def _on_session_started(self, client_id: str):
        self.current_session_client_id = client_id
        print(f"[Manager] Phiên làm việc với '{client_id}' đã bắt đầu.")
        self.session_started.emit(client_id)

    def _on_session_ended(self, client_id: str):
        print(f"[Manager] Phiên làm việc với '{client_id}' đã kết thúc.")
        if self.current_session_client_id == client_id:
            self.current_session_client_id = None
        self.session_ended.emit()
        self.app.request_client_list()

    def _on_error(self, error_msg: str):
        print(f"[Manager] Lỗi từ Server: {error_msg}")
        self.error_received.emit(error_msg)

    def _on_video_pdu(self, pdu: dict):
        if not self.current_session_client_id:
            return
        
        updated_img = self.viewer.process_video_pdu(self.current_session_client_id, pdu)
        
        if updated_img:
            self.video_pdu_received.emit(updated_img)
        
    def _on_file_pdu(self, pdu: dict):
        ptype = pdu.get("type")
        if ptype == "file_start":
            print(f"[Manager] {self.current_session_client_id} đang gửi file: {pdu.get('filename')}")
        
    def _on_control_pdu(self, pdu: dict):
        print(f"[Manager] Control PDU từ client: {pdu.get('message')}")

    # --- Slots (Hàm được gọi từ GUI) (Giữ nguyên) ---

    def _on_cursor_pdu(self, pdu: dict):
        if not self.current_session_client_id:
            return
        # pdu chứa x, y (đã chuẩn hóa), cursor_shape (bytes)
        self.cursor_pdu_received.emit(pdu) # Gửi thẳng dict PDU lên GUI/Viewer

    def gui_connect_to_client(self, client_id: str):
        if self.current_session_client_id:
            print(f"Lỗi: Đang trong phiên.")
            return
        if client_id not in self.client_list:
            print(f"Lỗi: Client {client_id} không có sẵn.")
            return
        self.app.connect_to_client(client_id)

    def gui_disconnect_session(self):
        if not self.current_session_client_id:
            print("Lỗi: Không ở trong phiên nào.")
            return
        self.app.disconnect_session()

    # --- SỬA HÀM NÀY ---
    def send_input_event(self, event: dict):
        """GUI gọi hàm này khi có sự kiện chuột/phím"""
        if not self.current_session_client_id:
            return 
        # Gửi sự kiện đã được format bởi GUI
        self.input_handler.send_event(event)

    # --- THÊM HÀM NÀY ---
    def _on_gui_input(self, event_dict: dict):
        """Nhận signal từ GUI và gửi đi"""
        self.send_input_event(event_dict)

# --- ĐIỂM VÀO CHÍNH (THAY THẾ TEST LOOP CŨ) ---

if __name__ == "__main__":
    # 1. Cấu hình
    HOST = "192.168.2.31"
    PORT = 3389
    MANAGER_ID = "manager_gui_1"

    # 2. Khởi tạo QApplication
    app = QApplication(sys.argv)

    # 3. Khởi tạo GUI
    window = ManagerWindow()
    
    # 4. Khởi tạo Logic Manager
    manager_logic = Manager(HOST, PORT, MANAGER_ID)
    
    # 5. Kết nối Logic và GUI
    manager_logic.client_list_updated.connect(window.update_client_list)
    manager_logic.session_started.connect(window.set_session_started)
    manager_logic.session_ended.connect(window.set_session_ended)
    manager_logic.video_pdu_received.connect(window.update_video_frame)
    manager_logic.cursor_pdu_received.connect(window.update_cursor_pos)
    manager_logic.error_received.connect(window.show_error)
    
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