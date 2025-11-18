import sys
import socket
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout,
    QHBoxLayout, QLineEdit, QFrame, QMessageBox, QSizePolicy,
    QScrollArea
)
from PyQt6.QtCore import Qt
from PyQt6.QtCore import pyqtSignal

from src.gui.ui_components import (
    DARK_BG, create_back_button
)

CARD_BG = "#181818"
TEXT_LIGHT = "#FFFFFF"
SUBTEXT = "#B3B3B3"
SPOTIFY_GREEN = "#1DB954"


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "Unknown"


class ClientWindow(QWidget):
    update_signal = pyqtSignal(list)
    def __init__(self, user, token):
        super().__init__()
        self.setWindowTitle("Client Panel")
        self.resize(1000, 600)
        self.setStyleSheet(f"background-color: {DARK_BG}; color: {TEXT_LIGHT};")

        self.user = user
        self.token = token
        self.is_editing = False

        self.init_ui()

    def init_ui(self):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        center_layout = QVBoxLayout()
        center_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card = QFrame()
        card.setStyleSheet(f"background-color: {CARD_BG}; border-radius: 12px;")
        card.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        card.setMaximumWidth(480)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(30, 30, 30, 30)
        card_layout.setSpacing(20)

        # --- Top bar ---
        top_bar = QHBoxLayout()
        title = QLabel("Client Panel")
        title.setStyleSheet("font-size: 18pt; font-weight: bold;")

        user_btn = QPushButton("📝")
        user_btn.setFixedSize(60, 60)
        user_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        user_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                font-size: 36pt;
                color: {SPOTIFY_GREEN};
            }}
            QPushButton:hover {{ color: #1ED760; }}
        """)
        user_btn.clicked.connect(self.on_profile)

        log_btn = QPushButton("Logout")
        log_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        log_btn.setFixedHeight(40)
        log_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {SPOTIFY_GREEN};
                color: {DARK_BG};
                font-size: 14px;
                border-radius: 8px;
                border: 1px solid {SPOTIFY_GREEN};
                padding: 4px 16px;
                margin-left: 16px;
                font-weight: bold;
                margin-top: 16px;
            }}
            QPushButton:hover {{
                background-color: #1ed760;
            }}
        """)
        log_btn.clicked.connect(self.Logout)

        top_bar.addWidget(title)
        top_bar.addStretch()
        top_bar.addWidget(user_btn)
        top_bar.addWidget(log_btn)

        # --- IP Display ---
        ip_label = QLabel("Your IP:")
        ip_label.setStyleSheet("font-size: 11pt;")

        self.ip_field = QLineEdit(get_local_ip())
        self.ip_field.setReadOnly(True)
        self.ip_field.setFixedHeight(36)
        self.ip_field.setMaximumWidth(240)
        self.ip_field.setStyleSheet(f"""
            QLineEdit {{
                background-color: #0f0f0f;
                border: none;
                padding: 6px 10px;
                border-radius: 8px;
                color: {TEXT_LIGHT};
                font-size: 11pt;
            }}
        """)

        copy_btn = QPushButton("  Copy  ")
        copy_btn.setFixedHeight(34)
        copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {SPOTIFY_GREEN};
                color: black;
                border-radius: 8px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #15a945; }}
        """)
        copy_btn.clicked.connect(self.copy_ip)

        ip_row = QHBoxLayout()
        ip_row.addWidget(self.ip_field)
        ip_row.addWidget(copy_btn)
        ip_row.addStretch()

        # --- Status + connect ---
        # self.status_label = QLabel("Status: Disconnected")
        # self.status_label.setMaximumWidth(260)
        # self.status_label.setStyleSheet(f"color: {SUBTEXT}; font-size: 10pt;")

        # self.connect_btn = QPushButton("Stop to connect")
        # self.connect_btn.setFixedHeight(38)
        # self.connect_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        # self.connect_btn.setStyleSheet(f"""
        #     QPushButton {{
        #         background-color: {SPOTIFY_GREEN};
        #         color: black;
        #         border-radius: 8px;
        #         font-weight: bold;
        #     }}
        #     QPushButton:pressed {{ background-color: #15a945; }}
        # """)

        card_layout.addLayout(top_bar)
        card_layout.addWidget(ip_label)
        card_layout.addLayout(ip_row)
        # card_layout.addWidget(self.status_label, alignment=Qt.AlignmentFlag.AlignLeft)
        # card_layout.addWidget(self.connect_btn)

        # --- Device List ---
        list_label = QLabel("Danh sách ghép nối:")
        list_label.setStyleSheet("font-size: 11pt; font-weight: bold;")

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background-color: transparent; border: none;")

        list_container = QFrame()
        self.list_layout = QVBoxLayout(list_container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(10)
        scroll.setWidget(list_container)

        # Danh sách client mẫu
        same, temp_list = QApplication.instance().conn.client_get_client_list(self.token)
        self.client_list = temp_list
        
        # self.client_list = [
        #     {"name": "Client A", "allowed": False},
        #     {"name": "Client B", "allowed": False},
        #     {"name": "Client C", "allowed": False},
        # ]

        self.render_client_list()

        card_layout.addWidget(list_label)
        card_layout.addWidget(scroll)

        center_layout.addWidget(card)
        outer_layout.addStretch()
        outer_layout.addLayout(center_layout)
        outer_layout.addStretch()
        
        self.update_signal.connect(self.update_list_ui)

        import threading
        threading.Thread(target=self.get_request_client_list, daemon=True).start()

        
    # --- Các hàm xử lý ---
    def render_client_list(self):
        for i in reversed(range(self.list_layout.count())):
            widget = self.list_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        for idx, client in enumerate(self.client_list):
            row = QHBoxLayout()
            name_label = QLabel(client["name"])
            name_label.setStyleSheet("font-size: 11pt;")

            toggle_btn = QPushButton("Cho phép" if client["allowed"] else "Từ chối")
            toggle_btn.setFixedWidth(100)
            toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            toggle_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {'#1DB954' if client["allowed"] else '#444'};
                    color: black;
                    border-radius: 8px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {'#15a945' if client["allowed"] else '#666'};
                }}
            """)
            toggle_btn.clicked.connect(lambda _, i=idx: self.toggle_client_permission(i))

            row.addWidget(name_label)
            row.addStretch()
            row.addWidget(toggle_btn)

            frame = QFrame()
            frame.setLayout(row)
            frame.setStyleSheet("background-color: #0f0f0f; border-radius: 8px; padding: 6px;")
            self.list_layout.addWidget(frame)

    def toggle_client_permission(self, index):
        client = self.client_list[index]
        client["allowed"] = not client["allowed"]
        # send gì đó
        if (client["allowed"]):
            QApplication.instance().conn.client_accepted_connect(self.token, client["name"])
        else:
            QApplication.instance().conn.client_remove_connect(self.token, client["name"])
        self.render_client_list()
    
    
    # tiến trình => gửi yêu cầu lên server và nhận danh sách , mỗi 30s gửi nhận 1 lần , nếu có thay đổi thì cập nhật lại giao diện
    # server sẽ lưu mỗi thay đổi của client , nếu có thay đổi mới thì = 1 và truy cập db, nếu không thì thôi 
    # tạo kết nối riêng để lấy danh sách client

    def update_list_ui(self, new_list):
        self.client_list = new_list
        self.render_client_list()   # SAFE (vì đang ở main thread)

    def get_request_client_list(self):
        from src.client.auth import ClientConnection
        import time
        AA = ClientConnection()
        while True:
            same, temp_list = AA.client_get_client_list(self.token)
            if same:
                self.update_signal.emit(temp_list)  # gửi signal về main thread

            time.sleep(10)
            
    def copy_ip(self):
        QApplication.clipboard().setText(self.ip_field.text())
        QMessageBox.information(self, "Copied", "IP address copied to clipboard!")

    def on_profile(self):
        from src.gui.profile import ProfileWindow
        self.profile_window = ProfileWindow(self.user, self.token)
        self.profile_window.showMaximized()
        self.close()

    def Logout(self):
        QApplication.instance().conn.client_logout(self.token)
        QApplication.instance().current_user = None
        from src.gui.signin import SignInWindow
        self.signin_window = SignInWindow()
        self.signin_window.showMaximized()
        self.close()
