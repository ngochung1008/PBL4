import sys
import os
import socket
import struct
import threading
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QFileDialog, QMessageBox
)
from PyQt5.QtCore import Qt

HOST = '10.136.201.25'
PORT = 5000

class ChatClient(QWidget):
    def __init__(self):
        super(ChatClient, self).__init__()
        self.setWindowTitle("Chat Client (PyQt5)")
        self.resize(600, 400)

        # Giao diện
        layout = QVBoxLayout()

        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        # layout.addWidget(self.chat_display)

        # Ô nhập + nút gửi
        input_layout = QHBoxLayout()
        self.msg_input = QLineEdit()
        self.msg_input.setPlaceholderText("Nhập tin nhắn...")
        input_layout.addWidget(self.msg_input)

        self.send_btn = QPushButton("Gửi")
        self.send_btn.clicked.connect(self.send_message)
        input_layout.addWidget(self.send_btn)

        self.file_btn = QPushButton("Gửi file")
        self.file_btn.clicked.connect(self.send_file_dialog)
        input_layout.addWidget(self.file_btn)

        layout.addLayout(input_layout)
        self.setLayout(layout)

        # Kết nối socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.sock.connect((HOST, PORT))
            self.chat_display.append("[KẾT NỐI] Đã kết nối tới server!")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi kết nối", str(e))
            sys.exit(1)

        # Luồng nhận dữ liệu
        threading.Thread(target=self.receive_messages, daemon=True).start()

    def receive_messages(self):
        """Nhận tin nhắn hoặc file"""
        while True:
            try:
                header = self.sock.recv(4)
                if not header:
                    break
                data_type = struct.unpack('!I', header)[0]

                if data_type == 1:  # Text
                    msg_len = struct.unpack('!I', self.sock.recv(4))[0]
                    msg = self.sock.recv(msg_len).decode()
                    self.chat_display.append(msg)

                elif data_type == 2:  # File
                    name_len = struct.unpack('!I', self.sock.recv(4))[0]
                    file_name = self.sock.recv(name_len).decode()
                    file_size = struct.unpack('!Q', self.sock.recv(8))[0]

                    file_data = b''
                    while len(file_data) < file_size:
                        chunk = self.sock.recv(4096)
                        if not chunk:
                            break
                        file_data += chunk

                    save_path = "received_" + file_name
                    with open(save_path, "wb") as f:
                        f.write(file_data)

                    self.chat_display.append(f"[ĐÃ NHẬN FILE] {file_name} ({file_size} bytes) -> lưu tại {save_path}")

            except Exception as e:
                self.chat_display.append(f"[LỖI] {e}")
                break

    def send_message(self):
        """Gửi tin nhắn"""
        msg = self.msg_input.text().strip()
        if msg:
            data = struct.pack('!I', 1) + struct.pack('!I', len(msg.encode())) + msg.encode()
            self.sock.sendall(data)
            self.msg_input.clear()

    def send_file_dialog(self):
        """Chọn file và gửi"""
        file_path, _ = QFileDialog.getOpenFileName(self, "Chọn file gửi")
        if file_path:
            self.send_file(file_path)

    def send_file(self, file_path):
        """Gửi file
            Params:
            - file_path (str): Đường dẫn tới file cần gửi
        """
        if not os.path.isfile(file_path):
            self.chat_display.append(f"[LỖI] Không tìm thấy file: {file_path}")
            return
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)

        with open(file_path, "rb") as f:
            file_data = f.read()

        data = (
            struct.pack('!I', 2) +
            struct.pack('!I', len(file_name.encode())) +
            file_name.encode() +
            struct.pack('!Q', file_size) +
            file_data
        )
        self.sock.sendall(data)
        self.chat_display.append(f"[ĐÃ GỬI FILE] {file_name} ({file_size} bytes)")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ChatClient()
    window.show()
    sys.exit(app.exec_())
