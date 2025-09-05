import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QTextEdit, QLineEdit, QSplitter, QFrame
)
from PyQt6.QtCore import Qt


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Client Manager")
        self.resize(900, 500)
        self.setStyleSheet("""
        QWidget {
            background-color: #00203F;   
            font-family: "Segoe UI";
        }
        QLineEdit, QPushButton, QListWidget, QTextEdit {
            background-color: #ADEFD1;   
        }
        """)
        # Layout chính
        main_layout = QHBoxLayout(self)

        # ======= Panel bên trái: List of clients =======
        left_panel = QFrame()
        left_layout = QVBoxLayout(left_panel)

        lbl_list = QLabel("List of clients")
        lbl_list.setStyleSheet("font-weight: bold; font-size: 16px; color: #00ffcc;")
        left_layout.addWidget(lbl_list)

        self.client_list = QListWidget()
        # Thêm dữ liệu mẫu
        item1 = QListWidgetItem("Name: Client1\nIP: 192.168.1.2   State: 1")
        item2 = QListWidgetItem("Name: Client2\nIP: 192.168.1.3   State: 0")
        self.client_list.addItem(item1)
        self.client_list.addItem(item2)
        left_layout.addWidget(self.client_list)

        # ======= Panel bên phải: Thông tin client =======
        right_panel = QFrame()
        right_layout = QVBoxLayout(right_panel)

        # Hàng trên: IP và More info
        top_info_layout = QHBoxLayout()
        self.txt_ip = QLineEdit()
        self.txt_ip.setPlaceholderText("IP .................")
        self.txt_ip.setFixedHeight(30)

        self.txt_info = QLineEdit()
        self.txt_info.setPlaceholderText("More info: ..................")
        self.txt_info.setFixedHeight(30)

        top_info_layout.addWidget(self.txt_ip)
        top_info_layout.addWidget(self.txt_info)
        right_layout.addLayout(top_info_layout)

        # Hàng nút
        button_layout = QHBoxLayout()
        self.btn_control = QPushButton("Control")
        self.btn_keystroke = QPushButton("View keystroke")
        self.btn_screen = QPushButton("View screen")
        self.btn_history = QPushButton("History")

        for btn in [self.btn_control, self.btn_keystroke, self.btn_screen, self.btn_history]:
            btn.setFixedHeight(35)
            button_layout.addWidget(btn)

        right_layout.addLayout(button_layout)

        # Vùng hiển thị (có thể phóng to)
        self.display_area = QTextEdit()
        self.display_area.setPlaceholderText("Hiển thị dữ liệu ở đây...")
        right_layout.addWidget(self.display_area, stretch=1)

        # Status bar
        self.lbl_status = QLabel("Current status: ................")
        right_layout.addWidget(self.lbl_status)

        # ======= Splitter để kéo dãn =======
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([200, 600])

        main_layout.addWidget(splitter)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())