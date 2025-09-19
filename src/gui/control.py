# control_server.py  (ví dụ)
import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QFrame, QSplitter, QListWidget, QLabel,
    QTextEdit, QPushButton, QStatusBar
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
        top_bar = QHBoxLayout()

        back_btn = create_back_button()
        top_bar.addWidget(back_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        search_user_box, self.search_user = create_search_bar("Search client by username or IP")

        top_bar.addStretch()
        top_bar.addWidget(search_user_box)

        main_layout.addLayout(top_bar)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter, stretch=1)

        sidebar = QFrame()
        sidebar.setStyleSheet(f"background-color: {CARD_BG}; border-radius: 6px;")
        sidebar_layout = QVBoxLayout(sidebar)

        lbl_clients = QLabel("Clients")
        lbl_clients.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        sidebar_layout.addWidget(lbl_clients)

        self.client_list = create_client_list()
        sidebar_layout.addWidget(self.client_list)

        self.client_list.addItem("user1 - 192.168.1.10")
        self.client_list.addItem("user2 - 192.168.1.11")
        self.client_list.addItem("user3 - 192.168.1.12")

        splitter.addWidget(sidebar)

        right_panel = QFrame()
        right_layout = QVBoxLayout(right_panel)

        self.server_ip_label = QLabel("Server IP: 192.168.1.1")
        self.server_ip_label.setStyleSheet("font-size: 12pt; font-weight: bold;")
        right_layout.addWidget(self.server_ip_label, alignment=Qt.AlignmentFlag.AlignLeft)

        btn_layout = QHBoxLayout()
        actions = ["Keylogger", "Screen", "Control", "File Transfer", "History"]
        for act in actions:
            btn = QPushButton(act)
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
        splitter.setSizes([250, 750])

        self.status = QStatusBar()
        self.status.setFixedHeight(22)
        self.status.setStyleSheet(f"""
            QStatusBar {{
                background-color: {CARD_BG};
                color: #1DB954;
                border-top: 1px solid {SUBTEXT};
            }}
        """)
        self.status.showMessage("Ready.")
        main_layout.addWidget(self.status)


def main():
    app = QApplication(sys.argv)
    win = ServerWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
