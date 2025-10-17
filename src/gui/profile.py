import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QMessageBox, QPushButton, QLineEdit, QFormLayout, QFrame
)
from PyQt6.QtCore import Qt

from src.gui.ui_components import (
    DARK_BG, create_card, create_title, create_input,
    create_primary_button, create_back_button
)

class ProfileWindow(QWidget):
    def __init__(self, user):
        print("OKe")
        super().__init__()
        self.setWindowTitle("Account Profile")
        self.resize(1000, 650)
        self.setStyleSheet(f"background-color: {DARK_BG};")
        self.is_editing = False
        self.user = user
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

        self.username = create_input(self.user.Username)
        self.full_name = create_input(self.user.FullName)
        self.email = create_input(self.user.Email)
        self.created_at = create_input(self.user.CreatedAt)
        self.last_login = create_input(self.user.LastLogin)
        self.role = create_input(self.user.Role)

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

        action_row = QHBoxLayout()
        action_row.addWidget(self.forgot_lbl)
        action_row.addStretch()
        action_row.addWidget(self.btn_change)

        card_layout.addWidget(info_widget)
        card_layout.addWidget(sep)
        card_layout.addWidget(pass_widget)
        card_layout.addSpacing(10)
        card_layout.addLayout(action_row)


        main_layout.addStretch()
        main_layout.addWidget(card, alignment=Qt.AlignmentFlag.AlignCenter)
        main_layout.addStretch()

    def go_back(self):
        QMessageBox.information(self, "Back", "Quay lại màn hình trước.")

    def toggle_edit(self):
        """Chuyển đổi giữa chế độ xem và chỉnh sửa"""
        if not self.is_editing:
            self.is_editing = True
            self.btn_change.setText("Save Change")
            for w in [self.username, self.full_name, self.email, self.role,
                      self.old_pass, self.new_pass]:
                w.setReadOnly(False)
        else:
            self.save_changes()

    def save_changes(self):
        """Lưu thay đổi & khoá form"""
        if self.old_pass.text().strip() or self.new_pass.text().strip():
            if not self.old_pass.text().strip() or not self.new_pass.text().strip():
                QMessageBox.warning(self, "Error",
                                    "Please fill in both old and new password.")
                return
            QMessageBox.information(self, "Password Changed",
                                    "Password updated successfully.")

        QMessageBox.information(self, "Saved", "Profile saved!")
        self.is_editing = False
        self.btn_change.setText("Change")

        for w in [
            self.username, self.full_name, self.email,
            self.created_at, self.last_login, self.role,
            self.old_pass, self.new_pass,
        ]:
            w.setReadOnly(True)

        self.old_pass.clear()
        self.new_pass.clear()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = ProfileWindow()
    win.show()
    sys.exit(app.exec())
