import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QFrame, QSplitter, QListWidget, QLabel,
    QTextEdit, QPushButton, QFormLayout
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from ui_components import (
    SPOTIFY_GREEN, DARK_BG, CARD_BG, TEXT_LIGHT, SUBTEXT,
    create_back_button, create_search_bar, create_client_list
)


class ServerWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Server Control Panel")
        self.setMinimumSize(1000, 600)
        self.setStyleSheet(f"background-color: {DARK_BG}; color: {TEXT_LIGHT};")
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        # ==== Thanh top: Back + Add Client ====
        top_bar = QHBoxLayout()
        back_btn = create_back_button()
        search_user_box, self.search_user = create_search_bar("Search client by username or IP")
        top_bar.addWidget(back_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        top_bar.addStretch()

        top_bar.addWidget(search_user_box)

        main_layout.addLayout(top_bar)

        # ==== Splitter trái/phải ====
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter, stretch=1)

        # ---------- BÊN TRÁI ----------
        sidebar = QFrame()
        sidebar.setStyleSheet(f"background-color: {CARD_BG}; border-radius: 6px;")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(12, 12, 12, 12)
        sidebar_layout.setSpacing(10)

        lbl_clients = QLabel("Clients")
        lbl_clients.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        sidebar_layout.addWidget(lbl_clients)

        self.client_list = QListWidget()
        self.client_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {DARK_BG};
                border-radius: 6px;
                padding: 4px;
                font-size: 11pt;
                color: {TEXT_LIGHT};
            }}
            QListWidget::item:selected {{
                background-color: {SPOTIFY_GREEN};
                color: black;
                border-radius: 4px;
            }}
        """)
        self.client_list.addItems([
            "Client : Alice ",
            "Client : Bob",
            "Client : Charlie",
            "Client : David"
        ])

        add_btn = QPushButton("Add Client")
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {SPOTIFY_GREEN};
                color: black;
                border-radius: 10px;
                padding: 6px 14px;
                font-weight: bold;
                margin-top: 16px;
            }}
            QPushButton:hover {{
                opacity: 0.85;
            }}
        """)
        self.client_list.currentRowChanged.connect(self.show_client_info)
        sidebar_layout.addWidget(self.client_list, stretch=1)
        sidebar_layout.addWidget(add_btn, alignment=Qt.AlignmentFlag.AlignBottom)

        # Khu vực thông tin chi tiết client
        self.info_frame = QFrame()
        self.info_frame.setStyleSheet(f"background-color: {DARK_BG}; border-radius: 8px;")
        info_layout = QFormLayout(self.info_frame)
        info_layout.setContentsMargins(10, 8, 10, 8)
        info_layout.setSpacing(6)
        self.lbl_username = QLabel("-")
        self.lbl_email = QLabel("-")
        self.lbl_ip = QLabel("-")

        for lbl in [self.lbl_username, self.lbl_email, self.lbl_ip]:
            lbl.setStyleSheet(f"color: {TEXT_LIGHT}; font-size: 10pt;")

        info_layout.addRow("Username:", self.lbl_username)
        info_layout.addRow("Email:", self.lbl_email)
        info_layout.addRow("IP:", self.lbl_ip)
        sidebar_layout.addWidget(self.info_frame)

        # Label trạng thái ngay dưới khung info
        self.lbl_status = QLabel("Status: -")
        self.lbl_status.setStyleSheet(f"font-size: 11pt; font-weight: bold; color: {SUBTEXT};")
        sidebar_layout.addWidget(self.lbl_status)

        splitter.addWidget(sidebar)

        # ---------- BÊN PHẢI ----------
        right_panel = QFrame()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(12, 12, 12, 12)
        right_layout.setSpacing(12)

        self.server_ip_label = QLabel("Server IP: 192.168.1.1")
        self.server_ip_label.setStyleSheet("font-size: 12pt; font-weight: bold;")
        right_layout.addWidget(self.server_ip_label, alignment=Qt.AlignmentFlag.AlignLeft)

        btn_layout = QHBoxLayout()
        actions = ["Keylogger", "Screen", "Control", "File Transfer", "All History"]
        for act in actions:
            btn = QPushButton(act)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {SPOTIFY_GREEN};
                    color: black;
                    border-radius: 8px;
                    padding: 8px 14px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    opacity: 0.85;
                }}
            """)
            btn_layout.addWidget(btn)
        right_layout.addLayout(btn_layout)

        self.action_area = QTextEdit()
        self.action_area.setPlaceholderText("Action output will appear here...")
        self.action_area.setStyleSheet(f"""
            QTextEdit {{
                background-color: {CARD_BG};
                border: 1px solid {SUBTEXT};
                border-radius: 8px;
                color: {TEXT_LIGHT};
                padding: 8px;
                font-size: 11pt;
            }}
        """)
        right_layout.addWidget(self.action_area, stretch=1)

        splitter.addWidget(right_panel)
        splitter.setSizes([300, 700])

        # Dữ liệu giả lập thông tin client
        self.client_data = {
            "Alice": {"email": "alice@example.com", "ip": "192.168.1.5", "status": "Connected"},
            "Bob": {"email": "bob@example.com", "ip": "192.168.1.8", "status": "Not connect"},
            "Charlie": {"email": "charlie@example.com", "ip": "192.168.1.12", "status": "Connected"},
            "David": {"email": "david@example.com", "ip": "192.168.1.20", "status": "Not connect"},
        }

    def show_client_info(self, index):
        if index < 0:
            self.lbl_username.setText("-")
            self.lbl_email.setText("-")
            self.lbl_ip.setText("-")
            self.lbl_status.setText("Status: -")
            return

        text = self.client_list.item(index).text()
        name = text.split(":")[1].split("(")[0].strip()
        data = self.client_data.get(name)
        if data:
            self.lbl_username.setText(name)
            self.lbl_email.setText(data["email"])
            self.lbl_ip.setText(data["ip"])
            # Màu cho trạng thái
            if data["status"].lower() == "connected":
                self.lbl_status.setStyleSheet(f"font-size: 11pt; font-weight: bold; color: {SPOTIFY_GREEN};")
            else:
                self.lbl_status.setStyleSheet(f"font-size: 11pt; font-weight: bold; color: gray;")
            self.lbl_status.setText(f"Status: {data['status']}")


def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    win = ServerWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
