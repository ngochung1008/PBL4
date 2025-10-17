from PIL import Image
from PyQt6.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout
from PyQt6.QtGui import QPixmap, QImage, QCursor
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QPoint
import socket, struct, io, time
from PIL import Image

class ScreenReceiver(QThread):
    frame_received = pyqtSignal(object)   # (qimage, w, h)
    connection_lost = pyqtSignal(str)

    def __init__(self, host, port, parent=None):
        super().__init__(parent)
        self.host = host
        self.port = port
        self._running = True

    def recv_all(self, sock, n):
        data = b""
        while len(data) < n:
            packet = sock.recv(n - len(data))
            if not packet:
                return None
            data += packet
        return data

    def run(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect((self.host, self.port))
                sock.sendall(b"MGR:")  # handshake
                while self._running:
                    header = self.recv_all(sock, 12)
                    if not header:
                        break
                    w, h, length = struct.unpack(">III", header)
                    data = self.recv_all(sock, length)
                    if not data:
                        break
                    img = Image.open(io.BytesIO(data)).convert("RGB")
                    bytes_per_line = 3 * img.width
                    qimg = QImage(img.tobytes(), img.width, img.height, 
                                bytes_per_line, QImage.Format.Format_RGB888)
                    qimg = qimg.copy()  # <-- THÊM này để đảm bảo buffer
                    self.frame_received.emit((qimg, w, h))
        except Exception as e:
            self.connection_lost.emit(str(e))

    def stop(self):
        self._running = False


class ManagerViewer(QWidget):
    def __init__(self, host, port):
        super().__init__()
        self.host = host
        self.port = port
        self.setWindowTitle("Remote Client Screen (Manager)")
        self.setGeometry(100, 100, 960, 540)
        self.label = QLabel("Đang nhận hình ảnh từ client...", self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("background-color: black;")
        layout = QVBoxLayout(self)
        layout.addWidget(self.label)
        self.setLayout(layout)

        # remote sizes
        self.remote_width = 1
        self.remote_height = 1

        # displayed image geometry in label
        self.display_w = 0
        self.display_h = 0
        self.offset_x = 0
        self.offset_y = 0

        # scale ratios (remote -> displayed)
        self.ratio_x = 1.0
        self.ratio_y = 1.0

        # overlay cursor representing remote client's pointer
        self.cursor_label = QLabel(self.label)
        self.cursor_label.setFixedSize(12, 12)
        self.cursor_label.setStyleSheet("background: red; border-radius: 6px; border: 2px solid white;")
        self.cursor_label.hide()

        # input handler reference (for ignore)
        self.input_handler = None

        # receiver thread
        self.receiver = ScreenReceiver(self.host, self.port)
        self.receiver.frame_received.connect(self.update_frame)
        self.receiver.connection_lost.connect(self.on_connection_lost)
        self.receiver.start()

    def set_input_handler(self, handler):
        self.input_handler = handler

    def update_frame(self, frame_info):
        qimg, w, h = frame_info
        self.remote_width = w
        self.remote_height = h

        pixmap = QPixmap.fromImage(qimg)
        label_size = self.label.size()
        scaled = pixmap.scaled(label_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.label.setPixmap(scaled)

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
    def label_coords_to_remote(self, lx, ly):
        """Chuyển tọa độ trong label sang tọa độ remote.
        Trả về None nếu nằm ngoài vùng hiển thị."""
        
        # Kiểm tra có nằm trong vùng hiển thị không
        rx_in = lx - self.offset_x
        ry_in = ly - self.offset_y
        
        if (rx_in < 0 or ry_in < 0 or 
            rx_in >= self.display_w or 
            ry_in >= self.display_h):
            return None

        # Chuyển sang tọa độ remote
        remote_x = int(rx_in / max(1.0, self.ratio_x))
        remote_y = int(ry_in / max(1.0, self.ratio_y))
        
        # Đảm bảo không vượt quá kích thước remote
        remote_x = max(0, min(self.remote_width - 1, remote_x))
        remote_y = max(0, min(self.remote_height - 1, remote_y))
        
        return remote_x, remote_y

    def remote_to_label_coords(self, remote_x, remote_y):
        lx = self.offset_x + int(remote_x * self.ratio_x)
        ly = self.offset_y + int(remote_y * self.ratio_y)
        return lx, ly

    def get_current_mapped_remote(self):
        global_pos = QCursor.pos()
        label_pos = self.label.mapFromGlobal(global_pos)
        if label_pos is None:
            return None
        lx, ly = label_pos.x(), label_pos.y()
        return self.label_coords_to_remote(lx, ly)

    def show_remote_cursor(self, remote_x, remote_y, move_system_cursor: bool = True):
        if self.remote_width <= 0 or self.remote_height <= 0:
            return
        lx, ly = self.remote_to_label_coords(remote_x, remote_y)
        w = self.cursor_label.width()
        h = self.cursor_label.height()
        self.cursor_label.move(max(0, lx - w // 2), max(0, ly - h // 2))
        self.cursor_label.show()

        if move_system_cursor:
            try:
                if self.input_handler:
                    self.input_handler.set_ignore(0.2)
                global_pos = self.label.mapToGlobal(QPoint(lx, ly))
                QCursor.setPos(global_pos)
            except Exception as e:
                print("[MANAGER VIEWER] Could not move system cursor:", e)

    def hide_remote_cursor(self):
        self.cursor_label.hide()

    def on_connection_lost(self, msg):
        self.label.setText(f"Mất kết nối tới client: {msg}")

    def closeEvent(self, event):
        self.receiver.stop()
        event.accept()