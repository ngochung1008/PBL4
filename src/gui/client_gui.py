import sys
import socket
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout,
    QHBoxLayout, QLineEdit, QFrame, QMessageBox, QSizePolicy
)
from PyQt6.QtCore import Qt

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

        self.status_label = QLabel("Status: Disconnected")
        self.status_label.setMaximumWidth(260)
        self.status_label.setStyleSheet(f"color: {SUBTEXT}; font-size: 10pt;")

        self.connect_btn = QPushButton("Stop to connect")
        self.connect_btn.setFixedHeight(38)
        self.connect_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.connect_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {SPOTIFY_GREEN};
                color: black;
                border-radius: 8px;
                font-weight: bold;
            }}
            QPushButton:pressed {{ background-color: #15a945; }}
        """)

        card_layout.addLayout(top_bar)
        card_layout.addWidget(ip_label)
        card_layout.addLayout(ip_row)
        card_layout.addWidget(self.status_label, alignment=Qt.AlignmentFlag.AlignLeft)
        card_layout.addWidget(self.connect_btn)

        center_layout.addWidget(card)
        outer_layout.addStretch()
        outer_layout.addLayout(center_layout)
        outer_layout.addStretch()


    def copy_ip(self):
        QApplication.clipboard().setText(self.ip_field.text())
        QMessageBox.information(self, "Copied", "IP address copied to clipboard!")

    def on_profile(self):
        from src.gui.profile import ProfileWindow
        self.profile_window = ProfileWindow(self.user, self.token)
        self.profile_window.showMaximized()
        self.close()

    def Logout(self):
        from src.client.auth import client_logout
        client_logout(self.token)
        QApplication.instance().current_user = None
        from src.gui.signin import SignInWindow
        self.signin_window = SignInWindow()
        self.signin_window.showMaximized()
        self.close()


def main():
    app = QApplication(sys.argv)
    win = ClientWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
