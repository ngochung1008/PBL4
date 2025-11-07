import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from src.gui.ui_components import DARK_BG, create_back_button

SPOTIFY_GREEN = "#1DB954"
CARD_BG = "#181818"
TEXT_LIGHT = "#FFFFFF"



class AddClientWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Add Client")
        self.resize(1000, 600)
        self.setMinimumSize(800, 450)
        self.setStyleSheet(f"background-color: {DARK_BG};")
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 20, 30, 20)
        main_layout.setSpacing(20)

        # --- Header ---
        header_layout = QHBoxLayout()
        self.back_btn = create_back_button()
        header_layout.addWidget(self.back_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        main_layout.addLayout(header_layout)

        # --- Center ---
        center_layout = QVBoxLayout()
        center_layout.setSpacing(16)
        center_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Input IP
        self.ip_edit = QLineEdit()
        self.ip_edit.setPlaceholderText("Enter client IP...")
        self.ip_edit.setFixedHeight(42)
        self.ip_edit.setFixedWidth(500)
        self.ip_edit.setStyleSheet(f"""
            QLineEdit {{
                background-color: {CARD_BG};
                color: {TEXT_LIGHT};
                padding: 8px 12px;
                border-radius: 8px;
                font-size: 15px;
            }}
        """)

        # Connect button
        self.btn_connect = QPushButton("Connect")
        self.btn_connect.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_connect.setFixedHeight(42)
        self.btn_connect.setFixedWidth(200)
        self.btn_connect.setStyleSheet(f"""
            QPushButton {{
                background-color: {SPOTIFY_GREEN};
                color: {DARK_BG};
                font-size: 16px;
                font-weight: bold;
                border-radius: 20px;
            }}
            QPushButton:hover {{
                background-color: #1ed760;
            }}
        """)
        self.btn_connect.clicked.connect(self.connect_client)
        
        # Status label
        self.status_label = QLabel("Status: Not connected")
        self.status_label.setFixedHeight(42)
        self.status_label.setFixedWidth(500)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet(f"""
            background-color: {CARD_BG};
            color: {SPOTIFY_GREEN};
            padding: 8px 12px;
            border-radius: 8px;
            font-size: 15px;
            margin-top: 12px;
        """)

        center_layout.addWidget(self.ip_edit, alignment=Qt.AlignmentFlag.AlignHCenter)
        center_layout.addWidget(self.btn_connect, alignment=Qt.AlignmentFlag.AlignHCenter)
        center_layout.addWidget(self.status_label, alignment=Qt.AlignmentFlag.AlignHCenter)

        main_layout.addItem(QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        main_layout.addLayout(center_layout)
        main_layout.addItem(QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        self.back_btn.clicked.connect(self.open_manage_clients)

    def open_manage_clients(self):
        from src.gui.manage_clients import ManageClientsWindow 
        self.manage_clients_window = ManageClientsWindow()
        self.manage_clients_window.show()
        self.close()

    def connect_client(self):
        username = self.ip_edit.text().strip()
        if not username:
            self.status_label.setText("Status: Please enter a valid username.")
            return
        if any(username == x for x, y in QApplication.instance().client_connected):
            self.status_label.setText(f"Status: Client {username} is already connected.")
            return
        try: 
            success, token = QApplication.instance().conn.client_check(username)
            if success:
                QApplication.instance().client_connected.append([username, token])
                self.status_label.setText(f"Status: Successfully connected to {username}.")
            else:
                self.status_label.setText(f"Status: Failed to connect to {username}.")
        except Exception as e:
            self.status_label.setText(f"Status: Error occurred - {str(e)}.")

