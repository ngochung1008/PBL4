# manager/manager_gui.py

import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QListWidget, QPushButton, QLabel, QListWidgetItem
)
from PyQt6.QtGui import (
    QPixmap, QImage, QMouseEvent, QKeyEvent, QPainter, QBrush, QPen, QPolygon
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QPoint
from PIL.ImageQt import toqimage

# --- THÊM: Map phím từ PyQt6 sang PyAutoGUI ---
key_map = {
    Qt.Key.Key_Backspace: 'backspace',
    Qt.Key.Key_Tab: 'tab',
    Qt.Key.Key_Return: 'enter',
    Qt.Key.Key_Enter: 'enter',
    Qt.Key.Key_Shift: 'shift',
    Qt.Key.Key_Control: 'ctrl',
    Qt.Key.Key_Alt: 'alt',
    Qt.Key.Key_Pause: 'pause',
    Qt.Key.Key_Escape: 'esc',
    Qt.Key.Key_Space: 'space',
    Qt.Key.Key_Delete: 'delete',
    Qt.Key.Key_Home: 'home',
    Qt.Key.Key_Left: 'left',
    Qt.Key.Key_Up: 'up',
    Qt.Key.Key_Right: 'right',
    Qt.Key.Key_Down: 'down',
    Qt.Key.Key_F1: 'f1', Qt.Key.Key_F2: 'f2', Qt.Key.Key_F3: 'f3',
    Qt.Key.Key_F4: 'f4', Qt.Key.Key_F5: 'f5', Qt.Key.Key_F6: 'f6',
    Qt.Key.Key_F7: 'f7', Qt.Key.Key_F8: 'f8', Qt.Key.Key_F9: 'f9',
    Qt.Key.Key_F10: 'f10', Qt.Key.Key_F11: 'f11', Qt.Key.Key_F12: 'f12',
}
# --- KẾT THÚC THÊM ---

class ManagerWindow(QMainWindow):
    connect_requested = pyqtSignal(str)
    disconnect_requested = pyqtSignal()
    
    # --- THÊM TÍN HIỆU INPUT ---
    input_event_generated = pyqtSignal(dict) # Một signal duy nhất cho tất cả event

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PBL4 - Remote Desktop Manager (PyQt6)")
        self.setGeometry(100, 100, 1200, 700)
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_panel.setMaximumWidth(250)
        
        self.client_list_widget = QListWidget()
        self.connect_btn = QPushButton("Kết nối (Connect)")
        self.disconnect_btn = QPushButton("Ngắt kết nối (Disconnect)")
        
        left_layout.addWidget(QLabel("Các Client đang rảnh:"))
        left_layout.addWidget(self.client_list_widget)
        left_layout.addWidget(self.connect_btn)
        left_layout.addWidget(self.disconnect_btn)
        
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        self.screen_label = QLabel("Chưa kết nối...")
        self.screen_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.screen_label.setStyleSheet("background-color: black; color: white;")
        
        # --- NÂNG CẤP: Bật theo dõi chuột & Focus ---
        self.screen_label.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        # --- KẾT THÚC NÂNG CẤP ---

        # Tọa độ con trỏ (chuẩn hóa 0.0-1.0)
        # Tọa độ PDU Cursor được Client gửi dưới dạng 0-10000
        self.current_cursor_norm_x = 0.5
        self.current_cursor_norm_y = 0.5

        # --- TẠO MŨI TÊN CON TRỎ TẠM THỜI (THAY CHO HÌNH VUÔNG ĐỎ) ---
        cursor_pixmap = QPixmap(24, 24) # Kích thước 24x24
        cursor_pixmap.fill(Qt.GlobalColor.transparent) 
        
        painter = QPainter(cursor_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Mũi tên màu đen với viền trắng (giống Windows)
        painter.setBrush(QBrush(Qt.GlobalColor.black)) 
        painter.setPen(QPen(Qt.GlobalColor.white, 2)) 
        
        # Vẽ tam giác đơn giản (Hotspot ~ (1, 1))
        points = [QPoint(1, 1), QPoint(1, 22), QPoint(15, 15), QPoint(1, 1)]
        painter.drawConvexPolygon(QPolygon(points))
        painter.end()
        
        self.cursor_pixmap_base = cursor_pixmap # Sử dụng mũi tên đã vẽ
        # --- KẾT THÚC TẠO MŨI TÊN ---
        
        # --- THÊM: CURSOR OVERLAY ---
        self.cursor_label = QLabel(self.screen_label)
        self.cursor_label.setStyleSheet("background-color: none;")
        self.cursor_label.setPixmap(self.cursor_pixmap_base)
        self.cursor_label.adjustSize()
        self.cursor_label.hide() 
        # --- KẾT THÚC THÊM ---

        right_layout.addWidget(self.screen_label)
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel, 1)

        self.connect_btn.clicked.connect(self.on_connect_click)
        self.disconnect_btn.clicked.connect(self.on_disconnect_click)
        
        self.current_client_id = None
        self.client_pixmap = QPixmap() # Lưu pixmap gốc
        self.update_button_states()

    def on_connect_click(self):
        selected_items = self.client_list_widget.selectedItems()
        if not selected_items:
            print("[GUI] Vui lòng chọn một client để kết nối.")
            return
        client_id = selected_items[0].text()
        self.connect_requested.emit(client_id)

    def on_disconnect_click(self):
        self.disconnect_requested.emit()

    def update_button_states(self):
        in_session = self.current_client_id is not None
        self.connect_btn.setEnabled(not in_session)
        self.disconnect_btn.setEnabled(in_session)
        self.client_list_widget.setEnabled(not in_session)

    # --- Sửa đổi hàm update_video_frame ---
    def update_video_frame(self, pil_image):
        """Nhận ảnh đã được vá từ Viewer và cập nhật Pixmap."""
        try:
            q_image = toqimage(pil_image)
            self.client_pixmap = QPixmap.fromImage(q_image) 
            self.update_scaled_pixmap() 
        except Exception as e:
            print(f"[GUI] Lỗi cập nhật frame: {e}")
            
    def update_scaled_pixmap(self):
        """Vẽ lại ảnh đã lưu vào label và cập nhật con trỏ"""
        if self.client_pixmap.isNull():
            return
            
        scaled_pixmap = self.client_pixmap.scaled(
            self.screen_label.size(), 
            Qt.AspectRatioMode.KeepAspectRatio, 
            Qt.TransformationMode.SmoothTransformation
        )
        self.screen_label.setPixmap(scaled_pixmap)
        self._update_cursor_overlay(scaled_pixmap)

    # --- THÊM: Xử lý sự kiện resize cửa sổ ---
    def resizeEvent(self, event):
        """Vẽ lại ảnh khi resize cửa sổ"""
        super().resizeEvent(event)
        if self.current_client_id:
            self.update_scaled_pixmap()

    # --- THÊM HÀM CẬP NHẬT VỊ TRÍ CON TRỎ ---
    def _update_cursor_overlay(self, scaled_pixmap: QPixmap):
        if self.current_client_id and not scaled_pixmap.isNull():
            
            label_size = self.screen_label.size()
            pixmap_size = scaled_pixmap.size()
            
            # Tính toán lề (giống _normalize_coords)
            offset_x = (label_size.width() - pixmap_size.width()) / 2
            offset_y = (label_size.height() - pixmap_size.height()) / 2
            
            # Tính tọa độ tuyệt đối trên QLabel
            x_abs = int(offset_x + pixmap_size.width() * self.current_cursor_norm_x)
            y_abs = int(offset_y + pixmap_size.height() * self.current_cursor_norm_y)
            
            # Đặt vị trí (trừ đi 1/2 kích thước con trỏ để căn giữa)
            cursor_w = self.cursor_label.pixmap().width()
            cursor_h = self.cursor_label.pixmap().height()
            
            self.cursor_label.move(x_abs - 1, y_abs - 1)
            self.cursor_label.show()
            self.cursor_label.update()
        else:
            self.cursor_label.hide()
            
    # --- THÊM SLOT NHẬN PDU CURSOR ---
    def update_cursor_pos(self, pdu: dict):
        """Nhận PDU cursor, cập nhật vị trí và hình dạng"""
        
        # Lỗi: PDU Parser trả về x, y là giá trị Integer (0-10000)
        # Chúng ta phải CHIA TỶ LỆ về 0.0-1.0
        x_int = pdu.get('x', 5000)
        y_int = pdu.get('y', 5000)
        
        # print(f"[GUI/CURSOR] Nhận: ({x_int}, {y_int})")
        
        # Chia tỷ lệ
        self.current_cursor_norm_x = x_int / 10000.0
        self.current_cursor_norm_y = y_int / 10000.0
        
        # TODO: Logic xử lý thay đổi hình dạng con trỏ (cursor_shape) tại đây
        
        if not self.screen_label.pixmap().isNull():
             self._update_cursor_overlay(self.screen_label.pixmap())

    # --- Slots (Hàm được gọi từ bên ngoài) ---
    def update_client_list(self, client_list: list):
        self.client_list_widget.clear()
        self.client_list_widget.addItems(client_list)

    def set_session_started(self, client_id: str):
        self.current_client_id = client_id
        self.screen_label.setText(f"Đang xem {client_id}...")
        self.update_button_states()
        self.setFocus() # Chuyển focus để bắt phím
        self.cursor_label.show()

    def set_session_ended(self):
        self.current_client_id = None
        self.screen_label.clear()
        self.screen_label.setText("Đã ngắt kết nối. Vui lòng chọn client.")
        self.client_pixmap = QPixmap() # Xóa ảnh
        self.screen_label.setPixmap(self.client_pixmap)
        self.update_button_states()
        self.cursor_label.hide()
        
    def show_error(self, message: str):
        print(f"--- LỖI TỪ SERVER: {message} ---")
        
    # --- NÂNG CẤP: HÀM XỬ LÝ INPUT ---

    def _normalize_coords(self, pos: QMouseEvent.pos):
        """Chuẩn hóa tọa độ chuột (0.0 -> 1.0)"""
        if self.client_pixmap.isNull():
            return None, None
            
        scaled_pixmap = self.screen_label.pixmap()
        if scaled_pixmap.isNull():
            return None, None

        label_size = self.screen_label.size()
        pixmap_size = scaled_pixmap.size()

        # Tính toán lề (do KeepAspectRatio)
        offset_x = (label_size.width() - pixmap_size.width()) / 2
        offset_y = (label_size.height() - pixmap_size.height()) / 2

        x = pos.x() - offset_x
        y = pos.y() - offset_y

        # Chuẩn hóa
        norm_x = x / pixmap_size.width()
        norm_y = y / pixmap_size.height()
        
        if 0 <= norm_x <= 1 and 0 <= norm_y <= 1:
            return norm_x, norm_y
        return None, None

    def mouseMoveEvent(self, event: QMouseEvent):
        if not self.current_client_id:
            return
        
        norm_x, norm_y = self._normalize_coords(event.pos())
        if norm_x is not None:
            self.input_event_generated.emit({
                "type": "mouse_move",
                "x_norm": norm_x,
                "y_norm": norm_y
            })

    def mousePressEvent(self, event: QMouseEvent):
        self.setFocus() # Click để focus
        if not self.current_client_id:
            return

        button = "left"
        if event.button() == Qt.MouseButton.RightButton:
            button = "right"
        elif event.button() == Qt.MouseButton.MiddleButton:
            button = "middle"
            
        norm_x, norm_y = self._normalize_coords(event.pos())
        if norm_x is not None:
            self.input_event_generated.emit({
                "type": "mouse_click",
                "button": button,
                "pressed": True, # Báo là nút được nhấn
                "x_norm": norm_x,
                "y_norm": norm_y
            })

    def mouseReleaseEvent(self, event: QMouseEvent):
        if not self.current_client_id:
            return
            
        button = "left"
        if event.button() == Qt.MouseButton.RightButton:
            button = "right"
        elif event.button() == Qt.MouseButton.MiddleButton:
            button = "middle"

        norm_x, norm_y = self._normalize_coords(event.pos())
        if norm_x is not None:
            self.input_event_generated.emit({
                "type": "mouse_click",
                "button": button,
                "pressed": False, # Báo là nút được thả
                "x_norm": norm_x,
                "y_norm": norm_y
            })
            
    def keyPressEvent(self, event: QKeyEvent):
        if not self.current_client_id:
            return
        
        key_name = self._get_key_name(event)
        if key_name and not event.isAutoRepeat(): # Bỏ qua phím lặp
            self.input_event_generated.emit({
                "type": "key_press",
                "key": key_name
            })

    def keyReleaseEvent(self, event: QKeyEvent):
        if not self.current_client_id:
            return
        
        key_name = self._get_key_name(event)
        if key_name and not event.isAutoRepeat(): # Bỏ qua phím lặp
            self.input_event_generated.emit({
                "type": "key_release",
                "key": key_name
            })
            
    def _get_key_name(self, event: QKeyEvent):
        key = event.key()
        if key in key_map:
            return key_map[key]
        
        text = event.text()
        if text.strip():
            return text.lower()
        
        # Xử lý các phím không in ra ký tự (ví dụ: Ctrl, Shift)
        if key == Qt.Key.Key_Control: return 'ctrl'
        if key == Qt.Key.Key_Shift: return 'shift'
        if key == Qt.Key.Key_Alt: return 'alt'
        
        return None