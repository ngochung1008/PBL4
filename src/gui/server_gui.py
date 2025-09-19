import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QPushButton, QLabel, QListWidget, QSplitter, QTextEdit, QFrame
)
from PyQt6.QtCore import Qt


class ClientMonitor(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Client Monitor")
        self.resize(900, 500)
        self.setStyleSheet("""
            QWidget {
                background-color: #150028;
                color: #A9FFD9;
                font-family: Consolas, monospace;
                font-size: 14px;
            }
            QPushButton {
                background-color: #30CFAF;
                color: #0A0020;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #25b597;
            }
            QLineEdit {
                background-color: #30CFAF;
                color: #0A0020;
                border-radius: 6px;
                padding: 4px;
            }
            QListWidget {
                background-color: #0A0020;
                border: 1px solid #30CFAF;
                border-radius: 6px;
            }
            QTextEdit {
                background-color: #0A0020;
                border: 1px solid #30CFAF;
                border-radius: 6px;
                color: #A9FFD9;
            }
            QLabel {
                font-weight: bold;
            }
        """)

        # Layout chính chia 2
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ======= Khung bên trái: List of clients =======
        left_frame = QFrame()
        left_layout = QVBoxLayout()

        lbl_list = QLabel("List of clients")
        search_box = QLineEdit()
        search_box.setPlaceholderText("Search...")

        self.client_list = QListWidget()
        self.client_list.addItem("Name: PC1 | IP: 192.168.1.2 | State: 1")
        self.client_list.addItem("Name: PC2 | IP: 192.168.1.3 | State: 0")

        left_layout.addWidget(lbl_list)
        left_layout.addWidget(search_box)
        left_layout.addWidget(self.client_list)
        left_frame.setLayout(left_layout)

        # ======= Khung bên phải: chi tiết =======
        right_frame = QFrame()
        right_layout = QVBoxLayout()

        # IP + More info
        top_info = QHBoxLayout()
        self.ip_field = QLineEdit()
        self.ip_field.setPlaceholderText("IP ...............")
        more_info = QLineEdit()
        more_info.setPlaceholderText("More info: ............................")

        top_info.addWidget(self.ip_field, 2)
        top_info.addWidget(more_info, 3)

        # Các nút Control
        btn_layout = QHBoxLayout()
        btn_control = QPushButton("Control")
        btn_key = QPushButton("View keystroke")
        btn_screen = QPushButton("View screen")
        btn_history = QPushButton("History")
        btn_layout.addWidget(btn_control)
        btn_layout.addWidget(btn_key)
        btn_layout.addWidget(btn_screen)
        btn_layout.addWidget(btn_history)

        # Màn hình chính
        self.display_area = QTextEdit()
        self.display_area.setPlaceholderText("Display area ...")

        # Trạng thái
        self.status_field = QLineEdit()
        self.status_field.setPlaceholderText("Current status: .................")

        # Gắn vào layout
        right_layout.addLayout(top_info)
        right_layout.addLayout(btn_layout)
        right_layout.addWidget(self.display_area)
        right_layout.addWidget(self.status_field)
        right_frame.setLayout(right_layout)

        # Thêm vào splitter
        splitter.addWidget(left_frame)
        splitter.addWidget(right_frame)
        splitter.setSizes([200, 600])

        # Layout chính
        main_layout = QHBoxLayout()
        main_layout.addWidget(splitter)
        self.setLayout(main_layout)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = ClientMonitor()
    win.show()
    sys.exit(app.exec())