import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout,
    QHBoxLayout, QFrame, QSizePolicy, QSpacerItem
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from src.gui.ui_components import DARK_BG, create_back_button

SPOTIFY_GREEN = "#1DB954"
CARD_BG = "#181818"
TEXT_LIGHT = "#FFFFFF"


class ServerWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.resize(1000, 600)
        self.setMinimumSize(800, 450)
        self.setStyleSheet(f"background-color: {DARK_BG}; color: {TEXT_LIGHT};")
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 20, 30, 20)
        main_layout.setSpacing(20)

        # ----------------- Thanh top -----------------
        top_layout = QHBoxLayout()
        top_layout.setSpacing(10)

        self.btn_back = create_back_button()
        top_layout.addWidget(self.btn_back, alignment=Qt.AlignmentFlag.AlignLeft)

        lbl_info = QLabel("ServerUser  |  192.168.1.100")
        lbl_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_info.setStyleSheet("font-size: 18px; font-weight: bold;")
        top_layout.addStretch()
        top_layout.addWidget(lbl_info)
        top_layout.addStretch()

        # Profile button
        self.btn_profile = QPushButton("Profile")
        self.btn_profile.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_profile.setStyleSheet(f"""
            QPushButton {{
                background-color: {SPOTIFY_GREEN};
                color: {DARK_BG};
                font-weight: bold;
                font-size: 14px;
                padding: 6px 16px;
                border-radius: 12px;
            }}
            QPushButton:hover {{
                background-color: #1ed760;
            }}
        """)
        top_layout.addWidget(self.btn_profile, alignment=Qt.AlignmentFlag.AlignRight)
        main_layout.addLayout(top_layout)

        # Spacer
        main_layout.addItem(QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        # ----------------- Container Options -----------------
        container = QFrame()
        container.setStyleSheet(f"""
            background-color: {CARD_BG};
            border-radius: 14px;
        """)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(40, 40, 40, 40)
        container_layout.setSpacing(25)
        container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_options = QLabel("Server Options")
        lbl_options.setStyleSheet("font-size: 20px; font-weight: bold;")
        lbl_options.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(lbl_options)

        self.btn_control = QPushButton("Control")
        self.btn_manage_screen = QPushButton("Manage All Screen")
        self.btn_manage_clients = QPushButton("Manage Clients")

        for btn in [self.btn_control, self.btn_manage_screen, self.btn_manage_clients]:
            btn.setFixedHeight(45)
            btn.setFixedWidth(300)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {SPOTIFY_GREEN};
                    color: {DARK_BG};
                    font-size: 16px;
                    font-weight: bold;
                    border-radius: 10px;
                }}
                QPushButton:hover {{
                    background-color: #1ed760;
                }}
            """)
            container_layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignHCenter)

        main_layout.addWidget(container, alignment=Qt.AlignmentFlag.AlignHCenter)
        main_layout.addItem(QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        # ----------------- Kết nối sự kiện -----------------
        self.btn_profile.clicked.connect(self.open_profile)
        self.btn_control.clicked.connect(self.open_control)
        self.btn_manage_screen.clicked.connect(self.open_manage_screens)
        self.btn_manage_clients.clicked.connect(self.open_manage_clients)

    # ----------------- Xử lý mở cửa sổ -----------------
    def open_profile(self):
        Token = QApplication.instance().current_user
        from src.model.Users import User
        data = QApplication.instance().conn.client_profile(Token)
        new_user = User(data[0], data[1], data[2], data[3], data[4], data[5], data[6], data[7])
        from src.gui.profile import ProfileWindow
        self.profile_window = ProfileWindow(new_user, Token)
        self.profile_window.show()
        self.close()
    def open_control(self):
        from src.gui.control import ControlWindow
        self.control_window = ControlWindow()
        self.control_window.show()
        self.close()
        
    def open_manage_screens(self):
        from src.gui.manage_screens import ManageScreensWindow
        self.screens_window = ManageScreensWindow()
        self.screens_window.show()
        self.close()

    def open_manage_clients(self):
        from src.gui.manage_clients import ManageClientsWindow
        self.clients_window = ManageClientsWindow()
        self.clients_window.show()
        self.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    win = ServerWindow()
    win.show()
    sys.exit(app.exec())
