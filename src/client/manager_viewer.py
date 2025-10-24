# manager_viewer.py

from PIL import Image
from PyQt6.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout
from PyQt6.QtGui import QPixmap, QImage, QCursor, QGuiApplication
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QPoint
import socket, struct, io, time
import config

MANAGER_IGNORE_DURATION_S = config.MANAGER_IGNORE_DURATION_S 

class CustomLabel(QLabel):
    # Sử dụng tín hiệu tùy chỉnh để thông báo cho ManagerViewer
    mouse_entered = pyqtSignal()
    mouse_left = pyqtSignal()
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setMouseTracking(True) # Bật theo dõi di chuột
        
    def enterEvent(self, event):
        self.mouse_entered.emit()
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        self.mouse_left.emit()
        super().leaveEvent(event)

# Lớp nhận frame qua socket trong thread riêng
class ScreenReceiver(QThread):
    # frame_received: phát khi nhận được một frame mới.
    frame_received = pyqtSignal(object)   # (qimage, w, h)
    # connection_lost: phát khi socket lỗi / kết nối mất; truyền thông báo lỗi dạng chuỗi.
    connection_lost = pyqtSignal(str)

    def __init__(self, host, port, parent=None):
        super().__init__(parent)
        self.host = host
        self.port = port
        self._running = True # flag để điều khiển vòng lặp run()
        self.sock = None # ⚡ THÊM: Lưu trữ socket
        self.target_ip = None # ⚡ THÊM: IP Client mục tiêu (nếu biết)

    def recv_all(self, sock, n):
        data = b"" # Khởi tạo buffer rỗng
        while len(data) < n:
            packet = sock.recv(n - len(data))
            if not packet:
                return None
            data += packet
        return data

    def run(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                self.sock = sock
                print(f"[MANAGER VIEWER] Attempting connection to screen {self.host}:{self.port}")
                sock.connect((self.host, self.port)) # kết nối tới server
                print("[MANAGER VIEWER] Connected to server for screen")

                sock.sendall(b"MGR:")  # handshake 
                self.send_select_command()
                while self._running:
                    header = self.recv_all(sock, 12)
                    if not header:
                        break
                    """ Nhận header gồm (width, height, length) 
                    Sử dụng thư viện struct để giải nén 12 byte header thành ba số nguyên 
                    32-bit không dấu (I) theo thứ tự big-endian (>). Ba giá trị này là: 
                    chiều rộng (w), chiều cao (h), và độ dài của dữ liệu hình ảnh (length). """
                    w, h, length = struct.unpack(">III", header)
                    print(f"[MANAGER VIEWER] Incoming frame header: {w}x{h}, {length} bytes")
                    data = self.recv_all(sock, length)
                    if not data:
                        break
                    # Giải mã hình ảnh từ bytes sang QImage
                    img = Image.open(io.BytesIO(data)).convert("RGB")
                    bytes_per_line = 3 * img.width # mỗi pixel có 3 byte (RGB)
                    # Tạo QImage từ dữ liệu hình ảnh
                    qimg = QImage(img.tobytes(), img.width, img.height, 
                                bytes_per_line, QImage.Format.Format_RGB888)
                    qimg = qimg.copy()
                    """Phát ra một tín hiệu (signal), mang theo QImage đã xử lý, chiều rộng (w) và chiều cao (h)."""
                    self.frame_received.emit((qimg, w, h))
        except Exception as e:
            """Phát ra tín hiệu thông báo lỗi khi kết nối bị mất."""
            self.connection_lost.emit(str(e))
            self.quit()
        finally:
            self.sock = None

    # Gửi lệnh chọn Client
    def send_select_command(self):
        """Gửi SELECT lệnh (ví dụ: SELECT:auto hoặc SELECT:IP)"""
        if self.sock:
            try:
                # Gửi lệnh yêu cầu Server tự động chọn Client đầu tiên
                command = "SELECT:auto\n" 
                self.sock.sendall(command.encode('utf-8'))
                print(f"[SCREEN RECEIVER] Sent SELECT:auto command.")
            except Exception as e:
                print(f"[SCREEN RECEIVER] Failed to send SELECT command: {e}")

    def stop(self):
        self._running = False

# Lớp UI chính hiển thị frame và con trỏ remote
class ManagerViewer(QWidget):
    def __init__(self, host, port):
        super().__init__()
        self.host = host
        self.port = port
        
        self.setWindowTitle("Remote Client Screen (Manager)")
        self.setGeometry(100, 100, 960, 540) # kích thước ban đầu (rộng 960, cao 540) đặt tại x=100, y=100
        
        self.label = CustomLabel("Đang nhận hình ảnh từ client...", self) # Tạo 1 đối tượng QLabel để hiển thị hình ảnh (frame) nhận được từ client. Ban đầu nó hiển thị thông báo chờ.
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter) # Căn giữa nội dung trong QLabel
        self.label.setStyleSheet("background-color: black;") # Đặt màu nền của QLabel là đen

        layout = QVBoxLayout(self) # QVBoxLayout (Vertical Box Layout) là một layout sắp xếp các widgets theo chiều dọc (từ trên xuống dưới)
        layout.addWidget(self.label)
        self.setLayout(layout)

        self.label.setMouseTracking(True)
        self._captured = False

        # remote sizes (kích thước thực màn hình)
        self.remote_width = 1
        self.remote_height = 1

        # displayed image geometry in label
        # (Kích thước thực tế ảnh được hiển thị trong QLabel sau khi đã scale)
        self.display_w = 0
        self.display_h = 0
        # offsets (label -> displayed image): độ lệch do hiệu ứng
        self.offset_x = 0
        self.offset_y = 0
        # scale ratios (remote -> displayed): tỉ lệ co giãn giữa màn hình remote và ảnh hiển thị
        self.ratio_x = 1.0
        self.ratio_y = 1.0

        """Tạo con trỏ nhỏ mô phỏng con trỏ của client từ xa."""
        # overlay cursor representing remote client's pointer
        self.cursor_label = QLabel(self.label)
        self.cursor_label.setFixedSize(12, 12)
        self.cursor_label.setStyleSheet("background: red; border-radius: 6px; border: 2px solid white;")
        self.cursor_label.hide() # ban đầu ẩn con trỏ đi 
        # Kết nối tín hiệu Enter/Leave
        self.label.mouse_entered.connect(self.handle_label_enter)
        self.label.mouse_left.connect(self.handle_label_leave)

        # input handler reference (for ignore)
        self.input_handler = None

        # receiver thread
        self.receiver = ScreenReceiver(self.host, self.port) # Tạo một đối tượng ScreenReceiver để nhận hình ảnh từ client
        self.receiver.frame_received.connect(self.update_frame) # Kết nối tín hiệu frame_received với hàm update_frame để cập nhật hình ảnh khi nhận được
        self.receiver.connection_lost.connect(self.on_connection_lost) # Kết nối tín hiệu connection_lost với hàm on_connection_lost để xử lý khi mất kết nối
        self.receiver.start() # Bắt đầu thread nhận luồng dữ liệu hình ảnh

    # Đặt tham chiếu cho input_handler
    def set_input_handler(self, handler):
        self.input_handler = handler

    # Ẩn con trỏ mô phỏng
    def hide_remote_cursor(self):
        self.cursor_label.hide()

    """ # Bật theo dõi sự kiện di chuột trên QLabel
    def set_label_cursor_tracking(self):
        # Bật theo dõi sự kiện di chuột ngay cả khi không có nút nào được nhấn
        self.label.setMouseTracking(True) """

    # Thêm vào class ManagerViewer

    def handle_label_enter(self):
        """Khi con trỏ Manager đi vào vùng hiển thị ảnh."""
        # Ẩn con trỏ hệ thống cục bộ
        QGuiApplication.setOverrideCursor(Qt.CursorShape.BlankCursor)
        # Hiển thị con trỏ mô phỏng (chấm đỏ) của client
        self.cursor_label.show() 
        # Nếu có input handler, bật chế độ control (manager có thể điều khiển)
        try:
            if self.input_handler:
                self.input_handler.is_controlling = True
                print("[MANAGER VIEWER] Input control ENABLED")
        except Exception as e:
            print("[MANAGER VIEWER] set control ON error:", e)
        
    def handle_label_leave(self):
        """Khi con trỏ Manager rời khỏi vùng hiển thị ảnh."""
        # Khôi phục con trỏ hệ thống cục bộ
        QGuiApplication.restoreOverrideCursor()
        # Ẩn con trỏ mô phỏng
        self.cursor_label.hide()
        try:
            if self.input_handler:
                self.input_handler.is_controlling = False
                print("[MANAGER VIEWER] Input control DISABLED")
        except Exception as e:
            print("[MANAGER VIEWER] set control OFF error:", e)

    """ # Hàm xử lý khi con trỏ chuột HỆ THỐNG đi vào QLabel
    def label_enterEvent(self, event):
        # Ẩn con trỏ chuột hệ thống của Manager
        QGuiApplication.setOverrideCursor(Qt.CursorShape.BlankCursor)
        # Giữ con trỏ mô phỏng (chấm đỏ) vẫn hiển thị
        self.cursor_label.show() 
        super().enterEvent(event)
    
    # Hàm xử lý khi con trỏ chuột HỆ THỐNG rời khỏi QLabel
    def label_leaveEvent(self, event):
        # Khôi phục con trỏ chuột hệ thống của Manager
        QGuiApplication.restoreOverrideCursor() 
        # Ẩn con trỏ mô phỏng
        self.cursor_label.hide()
        super().leaveEvent(event) """

    # Hiển thị thông báo mất kết nối lên self.label
    def on_connection_lost(self, msg):
        self.label.setText(f"Mất kết nối tới client: {msg}")

    # Được gọi khi cửa sổ đóng. Nó gọi self.receiver.stop() để dừng luồng nhận dữ liệu một cách an toàn trước khi đóng cửa sổ.
    def closeEvent(self, event):
        # Đảm bảo đóng receiver (luồng nhận màn hình)
        self.receiver.stop() # Dừng luồng nhận màn hình
        # Đóng socket input/cursor (nếu manager chủ động đóng cửa sổ)
        if hasattr(self, 'input_socket') and self.input_socket:
            try:
                self.input_socket.close()
            except Exception:
                pass
        event.accept()

    def update_frame(self, frame_info):
        qimg, w, h = frame_info # frame_info là một tuple (qimage, w, h)
        self.remote_width = w
        self.remote_height = h

        if qimg is None or qimg.isNull():
            print("[MANAGER VIEWER] Received empty QImage, skipping update.")
            return

        pixmap = QPixmap.fromImage(qimg) # Tạo QPixmap từ QImage nhận được
        label_size = self.label.size() # Lấy kích thước hiện tại của QLabel
        # Co giãn (scaled) QPixmap để vừa với label_size nhưng giữ nguyên tỉ lệ (KeepAspectRatio)
        scaled = pixmap.scaled(label_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.label.setPixmap(scaled) # Cập nhật QLabel với QPixmap đã co giãn

        self.display_w = scaled.width()
        self.display_h = scaled.height()

        self.offset_x = max(0, (label_size.width() - self.display_w) // 2)
        self.offset_y = max(0, (label_size.height() - self.display_h) // 2)

        self.ratio_x = self.display_w / max(1, self.remote_width)
        self.ratio_y = self.display_h / max(1, self.remote_height)

    def resizeEvent(self, event):
        if self.label.pixmap():
            self.label.setPixmap(self.label.pixmap().scaled(self.label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            self.display_w = self.label.pixmap().width()
            self.display_h = self.label.pixmap().height()
            self.offset_x = max(0, (self.label.size().width() - self.display_w) // 2)
            self.offset_y = max(0, (self.label.size().height() - self.display_h) // 2)
            if self.remote_width > 0:
                self.ratio_x = self.display_w / max(1, self.remote_width)
            if self.remote_height > 0:
                self.ratio_y = self.display_h / max(1, self.remote_height)
        super().resizeEvent(event)

    # --- mapping helpers ---
    # Thêm override xử lý chuột trên label: click để toggle control
    def label_mouse_press(self, event):
        # Toggle capture
        self._captured = not self._captured
        if self._captured:
            QGuiApplication.setOverrideCursor(Qt.CursorShape.BlankCursor)
            self.cursor_label.show()
            if self.input_handler:
                self.input_handler.is_controlling = True
            print("[MANAGER VIEWER] Capture ENABLED (click)")
        else:
            QGuiApplication.restoreOverrideCursor()
            self.cursor_label.hide()
            if self.input_handler:
                self.input_handler.is_controlling = False
            print("[MANAGER VIEWER] Capture DISABLED (click)")
        # don't call super here because label is a child widget; just accept event
        event.accept()

    # Hook up the handler in __init__ after label created:
    # self.label.mousePressEvent = self.label_mouse_press

    # Ánh xạ tọa độ Label <-> Remote screen (tọa độ chuột)
    def label_coords_to_remote(self, lx, ly):
        """Chuyển tọa độ trong label sang tọa độ remote.
        Trả về None nếu nằm ngoài vùng hiển thị."""
        
        # 1. Tọa độ tương đối bên trong ảnh hiển thị
        rx_in = lx - self.offset_x
        ry_in = ly - self.offset_y
        
        # 2. Kiểm tra có nằm trong vùng hiển thị không
        if (rx_in < 0 or ry_in < 0 or 
            rx_in >= self.display_w or 
            ry_in >= self.display_h):
            return None

        # 3. Chuyển sang tọa độ remote (chia cho tỉ lệ co giãn)
        remote_x = int(rx_in / max(1.0, self.ratio_x))
        remote_y = int(ry_in / max(1.0, self.ratio_y))
        
        # 4. Đảm bảo nằm trong giới hạn màn hình remote
        remote_x = max(0, min(self.remote_width - 1, remote_x))
        remote_y = max(0, min(self.remote_height - 1, remote_y))
        
        return remote_x, remote_y

    # Chuyển tọa độ remote sang tọa độ trong label
    def remote_to_label_coords(self, remote_x, remote_y):
        lx = self.offset_x + int(remote_x * self.ratio_x)
        ly = self.offset_y + int(remote_y * self.ratio_y)
        return lx, ly

    # Lấy tọa độ remote tương ứng với vị trí con trỏ hệ thống hiện tại
    def get_current_mapped_remote(self):
        global_pos = QCursor.pos()
        label_pos = self.label.mapFromGlobal(global_pos)
        # ... chuyển label_pos sang tọa độ remote bằng self.label_coords_to_remote ...
        if label_pos is None:
            return None
        lx, ly = label_pos.x(), label_pos.y()
        return self.label_coords_to_remote(lx, ly)

    def show_remote_cursor(self, remote_x, remote_y, move_system_cursor: bool = False):
        if self.remote_width <= 0 or self.remote_height <= 0:
            return
        lx, ly = self.remote_to_label_coords(remote_x, remote_y)
        w = self.cursor_label.width()
        h = self.cursor_label.height()

        # 1. Di chuyển và hiển thị con trỏ mô phỏng
        self.cursor_label.move(max(0, lx - w // 2), max(0, ly - h // 2))
        self.cursor_label.show()

        # 2. Di chuyển con trỏ hệ thống (Tùy chọn)
        # Chỉ di chuyển con trỏ hệ thống khi rõ ràng muốn do hành động local,
        # tránh auto-move mỗi khi nhận cursor_update từ client.
        if move_system_cursor and QGuiApplication.focusWindow():
            try:
                if self.input_handler:
                    # ... Sử dụng self.input_handler.set_ignore(0.2) để tránh loop feedback ...
                    self.input_handler.set_ignore(MANAGER_IGNORE_DURATION_S)
                global_pos = self.label.mapToGlobal(QPoint(lx, ly))
                QCursor.setPos(global_pos) # Di chuyển con trỏ chuột hệ thống.
            except Exception as e:
                print("[MANAGER VIEWER] Could not move system cursor:", e)
