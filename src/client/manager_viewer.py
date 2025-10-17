import socket
import struct
import io
from PIL import Image
from PyQt6.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout
from PyQt6.QtGui import QPixmap, QImage, QCursor
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QPoint
import sys
import math
import threading
import time

class ManagerViewer(QWidget):
    frame_received = pyqtSignal(object)
    connection_lost = pyqtSignal(str)

    def __init__(self, host, port):
        super().__init__()
        self.host = host
        self.port = port
        self.input_handler = None
        self.running = True
    
    def set_input_handler(self, handler):
        """Gắn ManagerInput để viewer có thể tạm vô hiệu hoá gửi khi di chuyển con trỏ hệ thống."""
        self.input_handler = handler

    def show_remote_cursor(self, remote_x, remote_y, move_system_cursor: bool = True):
        """Hiển thị overlay con trỏ vị trí remote trên label.
           Nếu move_system_cursor=True sẽ đặt con trỏ hệ thống của Manager trùng với remote cursor.
        """
        if self.remote_width <= 0 or self.remote_height <= 0:
            return
        lx, ly = self.remote_to_label_coords(remote_x, remote_y)
        # đặt vị trí sao cho con trỏ nằm giữa label
        w = self.cursor_label.width()
        h = self.cursor_label.height()
        self.cursor_label.move(max(0, lx - w // 2), max(0, ly - h // 2))
        self.cursor_label.show()

        if move_system_cursor:
            try:
                # tạm vô hiệu hoá gửi events do hành động này để tránh feedback loop
                if self.input_handler:
                    self.input_handler.set_ignore(0.2)  # 200ms ignore
                global_pos = self.label.mapToGlobal(QPoint(lx, ly))
                QCursor.setPos(global_pos)
            except Exception as e:
                print("[MANAGER VIEWER] Could not move system cursor:", e)

    def run(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect((self.host, self.port))
                sock.sendall(b"MGR:")  # Handshake for manager role
                print("[MANAGER VIEWER] Connected to server for screen stream")

                def recv_all(s, n):
                    data = b""
                    while len(data) < n:
                        packet = s.recv(n - len(data))
                        if not packet:
                            return None
                        data += packet
                    return data

                while self.running:
                    header = recv_all(sock, 12)
                    if not header:
                        break

                    w, h, length = struct.unpack(">III", header)
                    data = recv_all(sock, length)
                    if not data:
                        break

                    img = Image.open(io.BytesIO(data)).convert("RGB")
                    bytes_per_line = 3 * img.width
                    qimg = QImage(
                        img.tobytes(), img.width, img.height, bytes_per_line, QImage.Format.Format_RGB888
                    )

                    self.frame_received.emit((qimg, w, h))

        except Exception as e:
            self.connection_lost.emit(str(e))

        print("[MANAGER VIEWER] Connection closed.")

    def stop(self):
        self.running = False
        self.quit()
        self.wait()


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

        # Tạo luồng nhận hình
        self.receiver = ManagerViewer(self.host, self.port)
        self.receiver.frame_received.connect(self.update_frame)
        self.receiver.connection_lost.connect(self.on_connection_lost)
        self.receiver.start()

    def update_frame(self, frame_info):
        qimg, w, h = frame_info
        self.remote_width = w
        self.remote_height = h

        # tạo pixmap và scale đúng vào label theo KeepAspectRatio
        pixmap = QPixmap.fromImage(qimg)
        label_size = self.label.size()
        scaled = pixmap.scaled(
            label_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )
        self.label.setPixmap(scaled)

        # tính kích thước hiển thị và offset (để tính mapping chính xác)
        self.display_w = scaled.width()
        self.display_h = scaled.height()
        self.offset_x = max(0, (label_size.width() - self.display_w) // 2)
        self.offset_y = max(0, (label_size.height() - self.display_h) // 2)

        # tỷ lệ remote -> displayed
        self.ratio_x = self.display_w / max(1, self.remote_width)
        self.ratio_y = self.display_h / max(1, self.remote_height)

    def resizeEvent(self, event):
        if self.label.pixmap():
            self.label.setPixmap(
                self.label.pixmap().scaled(
                    self.label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
            # update display geometry on resize
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
        """Chuyển tọa độ (trong label) -> tọa độ remote pixel.
           Trả về (rx, ry) hoặc None nếu nằm ngoài vùng hình ảnh."""
        # đưa về tọa độ trong vùng ảnh
        rx_in = lx - self.offset_x
        ry_in = ly - self.offset_y
        if rx_in < 0 or ry_in < 0 or rx_in >= self.display_w or ry_in >= self.display_h:
            return None
        remote_x = int(rx_in / max(1.0, self.ratio_x))
        remote_y = int(ry_in / max(1.0, self.ratio_y))
        # clamp
        remote_x = max(0, min(self.remote_width - 1, remote_x))
        remote_y = max(0, min(self.remote_height - 1, remote_y))
        return remote_x, remote_y

    def remote_to_label_coords(self, remote_x, remote_y):
        """Chuyển tọa độ remote -> vị trí trong label (pixels)."""
        lx = self.offset_x + int(remote_x * self.ratio_x)
        ly = self.offset_y + int(remote_y * self.ratio_y)
        return lx, ly

    def get_current_mapped_remote(self):
        """Lấy vị trí con trỏ hiện tại trên màn hình manager, map về remote.
           Trả về (remote_x, remote_y) hoặc None nếu con trỏ nằm ngoài vùng hiển thị remote."""
        global_pos = QCursor.pos()
        label_pos = self.label.mapFromGlobal(global_pos)
        if label_pos is None:
            return None
        lx, ly = label_pos.x(), label_pos.y()
        return self.label_coords_to_remote(lx, ly)

    def show_remote_cursor(self, remote_x, remote_y):
        """Hiển thị overlay con trỏ vị trí remote trên label."""
        if self.remote_width <= 0 or self.remote_height <= 0:
            return
        lx, ly = self.remote_to_label_coords(remote_x, remote_y)
        # đặt vị trí sao cho con trỏ nằm giữa label
        w = self.cursor_label.width()
        h = self.cursor_label.height()
        self.cursor_label.move(max(0, lx - w // 2), max(0, ly - h // 2))
        self.cursor_label.show()

    def hide_remote_cursor(self):
        self.cursor_label.hide()

    def on_connection_lost(self, msg):
        self.label.setText(f"Mất kết nối tới client: {msg}")

    def closeEvent(self, event):
        print("[MANAGER VIEWER] Closing viewer...")
        self.receiver.stop()
        event.accept()