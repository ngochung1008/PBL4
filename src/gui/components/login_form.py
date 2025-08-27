from PyQt6.QtWidgets import (
    QApplication, QWidget, QLineEdit, QPushButton, QLabel, QVBoxLayout, QHBoxLayout, QFrame
)
from PyQt6.QtGui import QIcon, QFont, QAction
from PyQt6.QtCore import Qt
import sys


class LoginForm(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Login Form - PyQt6")
        self.setFixedSize(400, 300)
        self.setStyleSheet("""
            QWidget {
                background-color: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 pink, stop:1 black
                );
                font-family: "Segoe UI";
            }
            QLineEdit {
                border: 2px solid #dcdcdc;
                border-radius: 20px;
                padding: 10px 40px;
                background: pink;
                font-size: 14px;
            }
            QPushButton {
                background-color: pink;
                border-radius: 20px;
                padding: 10px;
                color: white;
                font-weight: bold;
                font-size: 15px;
            }
            QPushButton:hover {
                background-color: black;
            }
            QLabel {
                color: white;
                font-size: 18px;
                font-weight: bold;
            }
        """)

        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Title
        title = QLabel("Đăng nhập")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Username
        self.username = QLineEdit()
        self.username.setPlaceholderText("Tên đăng nhập")

        user_icon = QAction(QIcon.fromTheme("user"), "user", self.username)
        self.username.addAction(user_icon, QLineEdit.ActionPosition.LeadingPosition)

        # Password
        self.password = QLineEdit()
        self.password.setPlaceholderText("Mật khẩu")
        self.password.setEchoMode(QLineEdit.EchoMode.Password)

        lock_icon = QAction(QIcon.fromTheme("lock"), "lock", self.password)
        self.password.addAction(lock_icon, QLineEdit.ActionPosition.LeadingPosition)

        # Login button
        self.login_btn = QPushButton("Đăng nhập")
        self.login_btn.clicked.connect(self.check_login)

        layout.addWidget(self.username)
        layout.addWidget(self.password)
        layout.addWidget(self.login_btn)

        self.setLayout(layout)

    def check_login(self):
        user = self.username.text()
        pwd = self.password.text()
        if user == "admin" and pwd == "123456":
            self.show_message("Đăng nhập thành công ✅")
        else:
            self.show_message("Sai tài khoản hoặc mật khẩu ❌")

    def show_message(self, msg):
        label = QLabel(msg)
        label.setStyleSheet("color: yellow; font-size: 14px;")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout().addWidget(label)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LoginForm()
    window.show()
    sys.exit(app.exec())
