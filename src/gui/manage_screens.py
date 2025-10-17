import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QGridLayout, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from ui_components import DARK_BG, create_back_button

# Bảng màu
SPOTIFY_GREEN = "#1DB954"
DARK_BG = "#121212"
CARD_BG = "#181818"
TEXT_LIGHT = "#FFFFFF"
SUBTEXT = "#B3B3B3"


class ClientCard(QFrame):
    def __init__(self, username, ip):
        super().__init__()
        self.setStyleSheet(f"background-color: {CARD_BG}; border-radius: 8px;")
        self.setFixedSize(300, 200)  # --- tăng kích thước card

        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Vùng chứa màn hình + nút thu phóng
        screen_container = QFrame()
        screen_container.setStyleSheet(f"background-color: {DARK_BG}; border-radius: 4px;")
        screen_layout = QVBoxLayout(screen_container)
        screen_layout.setContentsMargins(4, 4, 4, 4)

        screen_placeholder = QLabel("Client Screen")
        screen_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        screen_placeholder.setStyleSheet(f"color: {SUBTEXT};")
        screen_placeholder.setFixedHeight(140)

        # Nút thu phóng
        zoom_btn = QPushButton("⤢")
        zoom_btn.setFixedSize(28, 28)
        zoom_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: transparent;
                color: {TEXT_LIGHT};
                font-size: 16px;
                border: none;
            }}
            QPushButton:hover {{
                color: {SPOTIFY_GREEN};
            }}
            """
        )
        zoom_btn.setToolTip("Phóng to màn hình")

        # Đặt nút thu phóng ở góc phải trên
        zoom_layout = QHBoxLayout()
        zoom_layout.addStretch()
        zoom_layout.addWidget(zoom_btn)
        zoom_layout.setContentsMargins(0, 0, 0, 0)

        screen_layout.addLayout(zoom_layout)
        screen_layout.addWidget(screen_placeholder)

        username_label = QLabel(username)
        username_label.setStyleSheet(f"color: {TEXT_LIGHT}; font-weight: bold;")

        ip_label = QLabel(ip)
        ip_label.setStyleSheet(f"color: {SUBTEXT}; font-size: 12px;")

        layout.addWidget(screen_container)
        layout.addWidget(username_label)
        layout.addWidget(ip_label)

        self.setLayout(layout)


class ManageScreensWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Server - Manage Clients")
        self.setStyleSheet(f"background-color: {DARK_BG};")

        # Kích thước khởi tạo
        self.resize(1100, 650)
        self.setMinimumSize(900, 500)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 10, 15, 10)
        main_layout.setSpacing(25)

        # Thanh trên cùng: Back + Title
        top_layout = QHBoxLayout()
        self.back_btn = create_back_button()
        top_layout.addWidget(self.back_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        top_layout.addStretch()

        main_layout.addLayout(top_layout)

        # Grid hiển thị client screens
        grid_layout = QGridLayout()
        grid_layout.setSpacing(8)  # --- giảm khoảng cách giữa các card

        sample_clients = [
            ("user1", "192.168.1.10"),
            ("user2", "192.168.1.11"),
            ("user3", "192.168.1.12"),
            ("user4", "192.168.1.13"),
            ("user5", "192.168.1.14"),
            ("user6", "192.168.1.15"),
        ]

        row, col = 0, 0
        for username, ip in sample_clients:
            card = ClientCard(username, ip)
            grid_layout.addWidget(card, row, col, alignment=Qt.AlignmentFlag.AlignTop)

            col += 1
            if col >= 3:  # 3 card mỗi hàng
                col = 0
                row += 1

        main_layout.addLayout(grid_layout, stretch=1)
        self.setLayout(main_layout)

        self.back_btn.clicked.connect(self.open_server_gui)
    def open_server_gui(self):
        import importlib
        mod = importlib.import_module("server_gui")
        ServerWindow = getattr(mod, "ServerWindow")
        self.server_gui = ServerWindow()
        self.server_gui.show()
        self.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ManageScreensWindow()
    window.show()
    sys.exit(app.exec())
