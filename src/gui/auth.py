from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QMessageBox, QFrame
)
from PyQt6.QtCore import Qt
import sys

SPOTIFY_GREEN = "#1DB954"
DARK_BG = "#121212"
CARD_BG = "#181818"
TEXT_LIGHT = "#FFFFFF"
SUBTEXT = "#B3B3B3"

class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sign In")
        self.setFixedSize(420, 500)
        self.setStyleSheet(f"background-color: {DARK_BG}; color: {TEXT_LIGHT};")
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(32, 28, 32, 28)

        # Card chứa nội dung
        card = QFrame()
        card.setStyleSheet(f"""
            background-color: {CARD_BG};
            border-radius: 12px;
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(28, 28, 28, 28)
        card_layout.setSpacing(18)

        # Tiêu đề
        title = QLabel("Sign In")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 20pt; font-weight: bold;")

        subtitle = QLabel("Welcome back — please sign in to continue")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet(f"color: {SUBTEXT}; font-size: 10pt;")

        # Username
        user_label = QLabel("Username")
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("Enter your username")
        self.user_input.setFixedHeight(40)
        self.user_input.setStyleSheet(self.input_qss())

        # Password + nút show/hide
        pass_label = QLabel("Password")
        pass_row = QHBoxLayout()
        self.pass_input = QLineEdit()
        self.pass_input.setPlaceholderText("Enter your password")
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pass_input.setFixedHeight(40)
        self.pass_input.setStyleSheet(self.input_qss())

        self.toggle_btn = QPushButton("👁")
        self.toggle_btn.setFixedSize(40, 40)
        self.toggle_btn.setStyleSheet("border: none; background: transparent; font-size: 12pt;")
        self.toggle_btn.clicked.connect(self.toggle_password)

        pass_row.addWidget(self.pass_input)
        pass_row.addWidget(self.toggle_btn)

        # Nút đăng nhập
        self.login_btn = QPushButton("Sign In")
        self.login_btn.setFixedHeight(46)
        self.login_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {SPOTIFY_GREEN};
                color: black;
                border: none;
                border-radius: 10px;
                font-weight: bold;
                font-size: 11pt;
            }}
            QPushButton:pressed {{
                background-color: #15a945;
            }}
        """)
        self.login_btn.clicked.connect(self.on_login)

        # Forgot + Register
        links_row = QHBoxLayout()
        self.forgot_btn = QPushButton("Forgot password?")
        self.forgot_btn.setStyleSheet(self.link_qss())
        self.forgot_btn.clicked.connect(self.on_forgot)

        self.register_btn = QPushButton("Sign up")
        self.register_btn.setStyleSheet(self.link_qss())
        self.register_btn.clicked.connect(self.on_register)

        links_row.addStretch()
        links_row.addWidget(self.forgot_btn)
        links_row.addWidget(self.register_btn)
        links_row.addStretch()

        # Footer
        footer = QLabel("By signing in, you agree to our Terms & Privacy Policy.")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet(f"color: {SUBTEXT}; font-size: 9pt;")

        # Assemble
        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)
        card_layout.addWidget(user_label)
        card_layout.addWidget(self.user_input)
        card_layout.addWidget(pass_label)
        card_layout.addLayout(pass_row)
        card_layout.addWidget(self.login_btn)
        card_layout.addLayout(links_row)
        card_layout.addWidget(footer)

        main_layout.addWidget(card)

    def input_qss(self):
        return f"""
            QLineEdit {{
                background-color: #0f0f0f;
                border: none;
                padding: 8px 10px;
                border-radius: 8px;
                color: {TEXT_LIGHT};
                font-size: 10.5pt;
            }}
            QLineEdit:focus {{
                border: 1px solid {SPOTIFY_GREEN};
            }}
        """

    def link_qss(self):
        return f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {SPOTIFY_GREEN};
                font-weight: 600;
                font-size: 10pt;
            }}
            QPushButton:hover {{
                text-decoration: underline;
            }}
        """

    def toggle_password(self):
        if self.pass_input.echoMode() == QLineEdit.EchoMode.Normal:
            self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        else:
            self.pass_input.setEchoMode(QLineEdit.EchoMode.Normal)

    def on_login(self):
        u, p = self.user_input.text().strip(), self.pass_input.text()
        if not u or not p:
            self.show_message("Error", "Please enter both username and password.")
        elif u == "test" and p == "123":
            self.show_message("Success", f"Welcome {u}!")
        else:
            self.show_message("Failed", "Invalid username or password.")

    def on_forgot(self):
        self.show_message("Forgot password", "Forgot password not implemented yet.")

    def on_register(self):
        self.show_message("Sign up", "Sign up not implemented yet.")

    def show_message(self, title, text):
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(text)
        msg.exec()

def main():
    app = QApplication(sys.argv)
    win = LoginWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
