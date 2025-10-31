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

class SignUpWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sign Up")
        self.resize(1100, 650)
        self.setStyleSheet(f"background-color: {DARK_BG};")
        self.init_ui()

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

        title = create_title("Sign Up", 28)
        subtitle = create_title("Welcome — please sign up to continue", 12)
        subtitle.setStyleSheet("color: #B3B3B3; font-size: 11pt; font-weight: normal;")

        self.user_input = create_input("Enter your username")
        self.user_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.fullname_input = create_input("Enter your full name")
        self.fullname_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        self.email_input = create_input("Enter your email")
        self.email_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        self.pass_input = create_input("Enter your password", password=True)
        self.pass_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        signup_btn = create_primary_button("Sign Up")
        signup_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        signup_btn.clicked.connect(self.sign_up)

        footer = QLabel("Already have an account?")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet("color:#B3B3B3; font-size:9pt;")

        sign_in_btn = QPushButton("Sign In")
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
        sign_in_btn.clicked.connect(self.sign_in)

        footer_row = QHBoxLayout()
        footer_row.addStretch()
        footer_row.addWidget(footer)
        footer_row.addWidget(sign_in_btn)
        footer_row.addStretch()

        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)
        card_layout.addSpacing(10)
        card_layout.addWidget(self.user_input)
        card_layout.addWidget(self.fullname_input)
        card_layout.addWidget(self.email_input)
        card_layout.addWidget(self.pass_input)
        card_layout.addWidget(signup_btn)
        card_layout.addLayout(footer_row)

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
        fullname = self.fullname_input.text().strip()
        email = self.email_input.text().strip()
        password = self.pass_input.text().strip()
        if not username or not password or not fullname or not email:
            QMessageBox.warning(None, "Error", "Please fill in all fields!")
            return
        success = QApplication.instance().conn.client_signup(username, password, fullname, email)
        if not success:
            QMessageBox.critical(None, "Error", "Sign up failed! Username may already exist.")
            return
        QMessageBox.information(None, "Success", f"Account created for {username}!")
        from src.gui.signin import SignInWindow
        self.signin_window = SignInWindow()
        self.signin_window.show()
        self.close()
    
    def sign_in(self):
        from src.gui.signin import SignInWindow
        self.signin_window = SignInWindow()
        self.signin_window.show()
        self.close()

# if __name__ == "__main__":
#     app = QApplication(sys.argv)
#     win = SignUpWindow()
#     win.showMaximized()   
#     sys.exit(app.exec())
