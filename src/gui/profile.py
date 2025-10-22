import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QMessageBox, QPushButton, QFormLayout, QFrame
)
from PyQt6.QtCore import Qt

from src.gui.ui_components import (
    DARK_BG, create_card, create_title, create_input,
    create_primary_button, create_back_button
)

LIGHT_TEXT = "#FFFFFF"


class ProfileWindow(QWidget):
    def __init__(self, user, token):
        super().__init__()
        print("ProfileWindow initialized")

        self.setWindowTitle("Account Profile")
        self.resize(1000, 650)
        self.setStyleSheet(f"background-color: {DARK_BG}; color: {LIGHT_TEXT};")

        # Lưu thông tin user và token
        self.user = user
        self.token = token
        self.is_editing = False

        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 20, 30, 20)
        main_layout.setSpacing(0)

        back_btn = create_back_button()
        back_btn.clicked.connect(self.go_back)
        main_layout.addWidget(back_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        card, card_layout = create_card()

        title = create_title("Account Information", 26)
        card_layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignHCenter)

        info_form = QFormLayout()
        info_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        info_form.setFormAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        info_form.setHorizontalSpacing(30)
        info_form.setVerticalSpacing(16)

        info_widget = QWidget()
        info_widget.setLayout(info_form)
        info_widget.setStyleSheet("""
            QLabel {
                color: #e0e0e0;
                font-size: 11pt;
            }
        """)

        # Nếu self.user là dict thì lấy key, nếu không thì dùng chuỗi
        username = self.user.get("Username") if isinstance(self.user, dict) else str(self.user)
        fullname = self.user.get("FullName", "") if isinstance(self.user, dict) else ""
        email = self.user.get("Email", "") if isinstance(self.user, dict) else ""
        created_at = self.user.get("CreatedAt", "") if isinstance(self.user, dict) else ""
        last_login = self.user.get("LastLogin", "") if isinstance(self.user, dict) else ""
        role = self.user.get("Role", "") if isinstance(self.user, dict) else ""

        self.username = create_input(username)
        self.full_name = create_input(fullname)
        self.email = create_input(email)
        self.created_at = create_input(created_at)
        self.last_login = create_input(last_login)
        self.role = create_input(role)

        pass_form = QFormLayout()
        pass_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        pass_form.setFormAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        pass_form.setHorizontalSpacing(30)
        pass_form.setVerticalSpacing(14)

        pass_widget = QWidget()
        pass_widget.setLayout(pass_form)
        pass_widget.setStyleSheet("""
            QLabel {
                color: #e0e0e0;
                font-size: 11pt;
            }
        """)

        self.old_pass = create_input("Old Password", password=True)
        self.new_pass = create_input("New Password", password=True)

        for w in [
            self.username, self.full_name, self.email,
            self.created_at, self.last_login, self.role,
            self.old_pass, self.new_pass,
        ]:
            w.setReadOnly(True)

        info_form.addRow("Username:", self.username)
        info_form.addRow("Full Name:", self.full_name)
        info_form.addRow("Email:", self.email)
        info_form.addRow("Created At:", self.created_at)
        info_form.addRow("Last Login:", self.last_login)
        info_form.addRow("Role:", self.role)

        pass_form.addRow("Old Password:", self.old_pass)
        pass_form.addRow("New Password:", self.new_pass)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #444; margin: 10px 0;")

        self.forgot_lbl = QLabel("Forgot password?")
        self.forgot_lbl.setStyleSheet("color:#1DB954; font-size:10pt;")
        self.forgot_lbl.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_change = create_primary_button("Change")
        self.btn_change.setFixedWidth(150)
        self.btn_change.clicked.connect(self.toggle_edit)

        token_label = QLabel(f"Access Token: {self.token}")
        token_label.setStyleSheet("color:#B3B3B3; font-size:10pt; margin-top:8px;")
        token_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        action_row = QHBoxLayout()
        action_row.addWidget(self.forgot_lbl)
        action_row.addStretch()
        action_row.addWidget(self.btn_change)

        card_layout.addWidget(info_widget)
        card_layout.addWidget(sep)
        card_layout.addWidget(pass_widget)
        card_layout.addSpacing(10)
        card_layout.addLayout(action_row)
        card_layout.addWidget(token_label)  

        main_layout.addStretch()
        main_layout.addWidget(card, alignment=Qt.AlignmentFlag.AlignCenter)
        main_layout.addStretch()

    def toggle_edit(self):
        self.is_editing = not self.is_editing
        editable = not self.username.isReadOnly()

        self.full_name.setReadOnly(editable)
        self.email.setReadOnly(editable)

        self.btn_change.setText("Cancel" if self.is_editing else "Change")

    def go_back(self):
        self.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    dummy_user = {"Username": "test_user", "FullName": "Test User", "Email": "test@example.com"}
    win = ProfileWindow(dummy_user, token="ABC123TOKEN")
    win.show()
    sys.exit(app.exec())
