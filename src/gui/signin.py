import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QMessageBox, QLabel, QPushButton, QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap

from src.gui.ui_components import (
    DARK_BG, create_card, create_title, create_input,
    create_primary_button, create_back_button
)

from src.client.auth import client_login
import threading

class SignInWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sign In")
        self.resize(1100, 650)
        self.setStyleSheet(f"background-color: {DARK_BG};")
        self.init_ui()
        self.token = None

    def init_ui(self):
        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        left_widget = QWidget()
        left_widget.setStyleSheet(f"background-color: {DARK_BG};")
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(40, 30, 40, 30)
        left_layout.setSpacing(20)

        card, card_layout = create_card()
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        title = create_title("Sign In", 28)
        subtitle = create_title("Welcome back — please sign in to continue", 12)
        subtitle.setStyleSheet("color: #B3B3B3; font-size: 11pt; font-weight: normal;")

        self.user_input = create_input("Enter your username")
        self.pass_input = create_input("Enter your password", password=True)

        signup_btn = create_primary_button("Sign In")
        signup_btn.clicked.connect(self.sign_up)

        footer = QLabel("You don't have account?")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet("color:#B3B3B3; font-size:9pt;")

        sign_in_btn = QPushButton("Sign Up")
        sign_in_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        sign_in_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #1DB954;
                font-weight: bold;
            }
            QPushButton:hover { text-decoration: underline; }
        """)

        forgot_pass_btn = QPushButton("Forgot password?")
        forgot_pass_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        forgot_pass_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #1DB954;
                font-weight: bold;
            }
            QPushButton:hover { text-decoration: underline; }
        """)

        footer_row = QHBoxLayout()
        footer_row.addStretch()
        footer_row.addWidget(footer)
        footer_row.addWidget(sign_in_btn)
        footer_row.addStretch()

        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)
        card_layout.addSpacing(10)
        card_layout.addWidget(self.user_input)
        card_layout.addWidget(self.pass_input)
        card_layout.addWidget(signup_btn)
        card_layout.addLayout(footer_row)
        card_layout.addWidget(forgot_pass_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        left_layout.addStretch()
        left_layout.addWidget(card, alignment=Qt.AlignmentFlag.AlignCenter)
        left_layout.addStretch()

        right_img = QLabel()
        right_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_img.setStyleSheet(f"background-color: {DARK_BG};")
        right_img.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        pixmap = QPixmap("image/image.png")
        if not pixmap.isNull():
            right_img.setPixmap(pixmap)
            right_img.setScaledContents(True)

        root_layout.addWidget(left_widget, stretch=3) 
        root_layout.addSpacing(40)                     
        root_layout.addWidget(right_img, stretch=2)     


    def sign_up(self):
        username = self.user_input.text().strip()
        password = self.pass_input.text().strip()
        
        if not username or not password:
            QMessageBox.warning(self, "Error", "Please fill in all fields!")
            return
        token = client_login(username, password) 
        if not token:
            QMessageBox.critical(None, "Error", "Sign in failed! Check your credentials.")
            return
        QMessageBox.information(None, "Success", f"Account created for {username}!")
        self.token = token 
        def load_user():
            from src.model.Users import get_user_by_sessionid
            user = get_user_by_sessionid(self.token)
            print(user)
            if user:
                from src.gui.profile import ProfileWindow
                self.profile_window = ProfileWindow(user)
                self.profile_window.showMaximized()
                self.close()

        threading.Thread(target=load_user).start()


    def dong(self):
        self.close()    


