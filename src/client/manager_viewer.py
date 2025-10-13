import socket
import struct
import io
from PIL import Image
from PyQt6.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtCore import QThread, pyqtSignal, Qt
import sys

class ScreenReceiver(QThread):
    frame_received = pyqtSignal(QImage)
    connection_lost = pyqtSignal(str)

    def __init__(self, host, port):
        super().__init__()
        self.host = host
        self.port = port
        self.running = True

    def run(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect((self.host, self.port))
                print("[MANAGER VIEWER] Connected to server for screen stream")

                while self.running:
                    # Nhận header (12 byte: width, height, length)
                    header = sock.recv(12)
                    if not header:
                        break

                    w, h, length = struct.unpack(">III", header)
                    data = b""
                    while len(data) < length:
                        packet = sock.recv(length - len(data))
                        if not packet:
                            break
                        data += packet

                    if not data:
                        break

                    # Giải mã ảnh JPEG -> QImage
                    img = Image.open(io.BytesIO(data)).convert("RGB")
                    qimg = QImage(
                        img.tobytes(), img.width, img.height, QImage.Format.Format_RGB888
                    )

                    # Phát tín hiệu ra để cập nhật GUI
                    self.frame_received.emit(qimg)

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

        layout = QVBoxLayout(self)
        layout.addWidget(self.label)
        self.setLayout(layout)

        # Tạo luồng nhận hình
        self.receiver = ScreenReceiver(self.host, self.port)
        self.receiver.frame_received.connect(self.update_frame)
        self.receiver.connection_lost.connect(self.on_connection_lost)
        self.receiver.start()

    def update_frame(self, qimg):
        pixmap = QPixmap.fromImage(qimg)
        self.label.setPixmap(pixmap.scaled(
            self.label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        ))

    def resizeEvent(self, event):
        if self.label.pixmap():
            self.label.setPixmap(
                self.label.pixmap().scaled(
                    self.label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )

    def on_connection_lost(self, msg):
        self.label.setText(f"Mất kết nối tới client: {msg}")

    def closeEvent(self, event):
        print("[MANAGER VIEWER] Closing viewer...")
        self.receiver.stop()
        event.accept()