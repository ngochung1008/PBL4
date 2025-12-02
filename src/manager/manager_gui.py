import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QListWidget, QPushButton, QLabel, QListWidgetItem
)
from PyQt6.QtGui import (
    QPixmap, QImage, QMouseEvent, QKeyEvent, QPainter, QBrush, QPen, QPolygon, QCursor
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QPoint, QEvent
from PIL.ImageQt import ImageQt # Dùng cái này an toàn hơn toqimage

# Map phím (Giữ nguyên)
key_map = {
    Qt.Key.Key_Backspace: 'backspace',
    Qt.Key.Key_Tab: 'tab',
    Qt.Key.Key_Return: 'enter',
    Qt.Key.Key_Enter: 'enter',
    Qt.Key.Key_Shift: 'shift',
    Qt.Key.Key_Control: 'ctrl',
    Qt.Key.Key_Alt: 'alt',
    Qt.Key.Key_Pause: 'pause',
    Qt.Key.Key_CapsLock: 'capslock', # Thêm Capslock
    Qt.Key.Key_Escape: 'esc',
    Qt.Key.Key_Space: 'space',
    Qt.Key.Key_PageUp: 'pgup',       # Thêm PageUp
    Qt.Key.Key_PageDown: 'pgdn',     # Thêm PageDown
    Qt.Key.Key_End: 'end',
    Qt.Key.Key_Home: 'home',
    Qt.Key.Key_Left: 'left',
    Qt.Key.Key_Up: 'up',
    Qt.Key.Key_Right: 'right',
    Qt.Key.Key_Down: 'down',
    Qt.Key.Key_Print: 'printscreen', # Thêm Chụp màn hình
    Qt.Key.Key_Insert: 'insert',
    Qt.Key.Key_Delete: 'delete',
    Qt.Key.Key_Meta: 'win',          # QUAN TRỌNG: Phím Windows
    Qt.Key.Key_Super_L: 'win',       # Dự phòng cho Linux/Mac
    Qt.Key.Key_Super_R: 'win',
    
    # Các phím F1-F12
    Qt.Key.Key_F1: 'f1', Qt.Key.Key_F2: 'f2', Qt.Key.Key_F3: 'f3',
    Qt.Key.Key_F4: 'f4', Qt.Key.Key_F5: 'f5', Qt.Key.Key_F6: 'f6',
    Qt.Key.Key_F7: 'f7', Qt.Key.Key_F8: 'f8', Qt.Key.Key_F9: 'f9',
    Qt.Key.Key_F10: 'f10', Qt.Key.Key_F11: 'f11', Qt.Key.Key_F12: 'f12',
}

class ManagerWindow(QMainWindow):
    connect_requested = pyqtSignal(str)
    disconnect_requested = pyqtSignal()
    input_event_generated = pyqtSignal(dict) 

    def __init__(self):
        super().__init__()
        
        # --- [SỬA] KHAI BÁO BIẾN TRẠNG THÁI TRƯỚC TIÊN ---
        self.current_client_id = None 
        self.client_pixmap = QPixmap()
        # --------------------------------------------------

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
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        self.screen_label = QLabel("Chưa kết nối...")
        self.screen_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.screen_label.setStyleSheet("background-color: black; color: white;")
        
        # --- QUAN TRỌNG: Bật MouseTracking cho Label ---
        self.screen_label.setMouseTracking(True)
        # Cài đặt Event Filter (Giờ biến current_client_id đã tồn tại nên sẽ không lỗi)
        self.screen_label.installEventFilter(self)
        
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.last_mouse_sent_time = 0
        self.current_cursor_norm_x = 0.5
        self.current_cursor_norm_y = 0.5

        # --- Tạo con trỏ ảo ---
        cursor_pixmap = QPixmap(24, 24)
        cursor_pixmap.fill(Qt.GlobalColor.transparent) 
        painter = QPainter(cursor_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QBrush(Qt.GlobalColor.black)) 
        painter.setPen(QPen(Qt.GlobalColor.white, 2)) 
        points = [QPoint(1, 1), QPoint(1, 22), QPoint(15, 15), QPoint(1, 1)]
        painter.drawConvexPolygon(QPolygon(points))
        painter.end()
        self.cursor_pixmap_base = cursor_pixmap 
        
        self.cursor_label = QLabel(self.screen_label)
        self.cursor_label.setStyleSheet("background-color: none;")
        self.cursor_label.setPixmap(self.cursor_pixmap_base)
        self.cursor_label.adjustSize()
        self.cursor_label.hide() 

        right_layout.addWidget(self.screen_label)
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel, 1)

        self.connect_btn.clicked.connect(self.on_connect_click)
        self.disconnect_btn.clicked.connect(self.on_disconnect_click)
        
        self.update_button_states()

    # --- SỬ DỤNG EVENT FILTER ĐỂ BẮT CHUỘT MƯỢT HƠN ---
    def eventFilter(self, source, event):
        """
        Bắt sự kiện trực tiếp từ screen_label.
        Giúp chuột di chuyển mượt mà không cần click.
        """
        if source == self.screen_label and self.current_client_id:
            if event.type() == QEvent.Type.MouseMove:
                self._handle_mouse_move(event)
                return True # Đã xử lý, không cần gửi tiếp
            elif event.type() == QEvent.Type.MouseButtonPress:
                self.setFocus() # Focus để nhận phím
                self._handle_mouse_click(event, pressed=True)
                return True
            elif event.type() == QEvent.Type.MouseButtonRelease:
                self._handle_mouse_click(event, pressed=False)
                return True
            # Tùy chọn: Ẩn con trỏ thật khi vào vùng video
            elif event.type() == QEvent.Type.Enter:
                self.screen_label.setCursor(Qt.CursorShape.BlankCursor)
            elif event.type() == QEvent.Type.Leave:
                self.screen_label.setCursor(Qt.CursorShape.ArrowCursor)
                
        return super().eventFilter(source, event)

    def _handle_mouse_move(self, event: QMouseEvent):
        # [THÊM] Logic Throttle (Giới hạn tốc độ gửi)
        # Chỉ gửi nếu cách lần trước ít nhất 30ms (khoảng 33 FPS)
        import time
        now = time.time() * 1000
        if now - self.last_mouse_sent_time < 30: 
            # Vẫn cập nhật con trỏ ảo trên màn hình mình cho mượt
            norm_x, norm_y = self._calculate_norm_coords(event.pos())
            if norm_x is not None:
                self._move_cursor_overlay_to_norm(norm_x, norm_y)
            return # Nhưng KHÔNG GỬI qua mạng

        # Tính toán tọa độ
        norm_x, norm_y = self._calculate_norm_coords(event.pos())
        
        if norm_x is not None:
            self.current_cursor_norm_x = norm_x
            self.current_cursor_norm_y = norm_y
            self._move_cursor_overlay_to_norm(norm_x, norm_y)
            
            # Gửi tọa độ qua mạng
            self.input_event_generated.emit({
                "type": "mouse_move",
                "x_norm": norm_x,
                "y_norm": norm_y
            })
            self.last_mouse_sent_time = now # Cập nhật thời gian gửi

    def _handle_mouse_click(self, event: QMouseEvent, pressed: bool):
        button = "left"
        if event.button() == Qt.MouseButton.RightButton: button = "right"
        elif event.button() == Qt.MouseButton.MiddleButton: button = "middle"
        
        norm_x, norm_y = self._calculate_norm_coords(event.pos())
        
        if norm_x is not None:
            self.input_event_generated.emit({
                "type": "mouse_click",
                "button": button,
                "pressed": pressed,
                "x_norm": norm_x,
                "y_norm": norm_y
            })

    def _calculate_norm_coords(self, local_pos: QPoint):
        """Tính tọa độ chuẩn hóa từ vị trí chuột TRONG label"""
        if self.client_pixmap.isNull(): return None, None
        
        label_size = self.screen_label.size()
        scaled_pixmap = self.screen_label.pixmap()
        if not scaled_pixmap: return None, None
        pixmap_size = scaled_pixmap.size()

        # Lề đen do KeepAspectRatio
        offset_x = (label_size.width() - pixmap_size.width()) / 2
        offset_y = (label_size.height() - pixmap_size.height()) / 2

        # Tọa độ tương đối trên ảnh
        x = local_pos.x() - offset_x
        y = local_pos.y() - offset_y

        norm_x = x / pixmap_size.width()
        norm_y = y / pixmap_size.height()

        if 0 <= norm_x <= 1 and 0 <= norm_y <= 1:
            return norm_x, norm_y
        return None, None

    def _move_cursor_overlay_to_norm(self, norm_x, norm_y):
        """Di chuyển con trỏ ảo đến vị trí chuẩn hóa"""
        if self.screen_label.pixmap() and not self.screen_label.pixmap().isNull():
            label_size = self.screen_label.size()
            pixmap_size = self.screen_label.pixmap().size()
            
            offset_x = (label_size.width() - pixmap_size.width()) / 2
            offset_y = (label_size.height() - pixmap_size.height()) / 2
            
            x_abs = int(offset_x + pixmap_size.width() * norm_x)
            y_abs = int(offset_y + pixmap_size.height() * norm_y)
            
            # Trừ nhẹ để mũi tên trỏ đúng điểm
            self.cursor_label.move(x_abs - 1, y_abs - 1)
            self.cursor_label.show()

    # --- Cập nhật ảnh Video ---
    def update_video_frame(self, pil_image):
        try:
            q_image = ImageQt(pil_image)
            self.client_pixmap = QPixmap.fromImage(q_image.copy()) 
            self.update_scaled_pixmap()
        except Exception as e:
            print(f"[GUI] Lỗi cập nhật frame: {e}")

    def update_scaled_pixmap(self):
        if self.client_pixmap.isNull(): return
        
        scaled_pixmap = self.client_pixmap.scaled(
            self.screen_label.size(), 
            Qt.AspectRatioMode.KeepAspectRatio, 
            Qt.TransformationMode.SmoothTransformation
        )
        self.screen_label.setPixmap(scaled_pixmap)
        
        # Cập nhật lại vị trí con trỏ theo tỷ lệ mới (nếu đang resize)
        self._move_cursor_overlay_to_norm(self.current_cursor_norm_x, self.current_cursor_norm_y)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.current_client_id:
            self.update_scaled_pixmap()

    # --- Nhận vị trí chuột từ Client (Remote Loopback) ---
    def update_cursor_pos(self, pdu: dict):
        """
        Nhận PDU cursor từ Client gửi về.
        Chỉ cập nhật nếu chuột của Manager ĐANG KHÔNG nằm trong vùng video.
        (Tránh xung đột: tay mình di qua trái, tín hiệu client báo về qua phải -> Rung lắc)
        """
        # Nếu chuột manager đang ở trong vùng screen_label, ta ưu tiên hiển thị chuột manager
        if self.screen_label.underMouse():
            return 

        x_int = pdu.get('x', 5000)
        y_int = pdu.get('y', 5000)
        
        self.current_cursor_norm_x = x_int / 10000.0
        self.current_cursor_norm_y = y_int / 10000.0
        
        self._move_cursor_overlay_to_norm(self.current_cursor_norm_x, self.current_cursor_norm_y)

    # --- Connect/Disconnect ---
    def on_connect_click(self):
        items = self.client_list_widget.selectedItems()
        if items: self.connect_requested.emit(items[0].text())

    def on_disconnect_click(self):
        self.disconnect_requested.emit()

    def update_client_list(self, client_list):
        self.client_list_widget.clear()
        self.client_list_widget.addItems(client_list)

    def set_session_started(self, client_id):
        self.current_client_id = client_id
        self.screen_label.setText(f"Đang xem {client_id}...")
        self.update_button_states()
        self.setFocus()
        self.cursor_label.show()

    def set_session_ended(self):
        self.current_client_id = None
        self.screen_label.clear()
        self.screen_label.setText("Đã ngắt kết nối.")
        self.client_pixmap = QPixmap()
        self.screen_label.setPixmap(self.client_pixmap)
        self.update_button_states()
        self.cursor_label.hide()
        self.screen_label.setCursor(Qt.CursorShape.ArrowCursor) # Hiện lại chuột thật

    def update_button_states(self):
        in_session = self.current_client_id is not None
        self.connect_btn.setEnabled(not in_session)
        self.disconnect_btn.setEnabled(in_session)
        self.client_list_widget.setEnabled(not in_session)

    def show_error(self, message):
        print(f"--- LỖI SERVER: {message} ---")

    # --- Keyboard Events (Giữ nguyên) ---
    def keyPressEvent(self, event: QKeyEvent):
        if not self.current_client_id: return
        key_name = self._get_key_name(event)
        if key_name and not event.isAutoRepeat():
            self.input_event_generated.emit({"type": "key_press", "key": key_name})

    def keyReleaseEvent(self, event: QKeyEvent):
        if not self.current_client_id: return
        key_name = self._get_key_name(event)
        if key_name and not event.isAutoRepeat():
            self.input_event_generated.emit({"type": "key_release", "key": key_name})

    def _get_key_name(self, event: QKeyEvent):
        key = event.key()
        if key in key_map: return key_map[key]
        text = event.text()
        if text.strip(): return text.lower()
        if key == Qt.Key.Key_Control: return 'ctrl'
        if key == Qt.Key.Key_Shift: return 'shift'
        if key == Qt.Key.Key_Alt: return 'alt'
        return None