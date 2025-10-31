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
    def __init__(self, user, token ):
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
        username = self.user.Username
        fullname = self.user.FullName
        email = self.user.Email
        created_at = self.user.CreatedAt
        last_login = self.user.LastLogin
        role = self.user.Role

        self.username = create_input(username)
        self.full_name = create_input(fullname)
        self.email = create_input(email)
        self.created_at = create_input(created_at.strftime("%Y-%m-%d %H:%M:%S") if created_at else "")
        self.last_login = create_input(last_login.strftime("%Y-%m-%d %H:%M:%S") if last_login else "")
        self.role = create_input(role)

        self.username.setText(self.user.Username)
        self.full_name.setText(self.user.FullName)
        self.email.setText(self.user.Email)
        self.created_at.setText(self.user.CreatedAt.strftime("%Y-%m-%d %H:%M:%S") if self.user.CreatedAt else "")
        self.last_login.setText(self.user.LastLogin.strftime("%Y-%m-%d %H:%M:%S") if self.user.LastLogin else "")
        self.role.setText(self.user.Role)

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
            self.username, # self.full_name, self.email,
            self.created_at, self.last_login, self.role,
            # self.old_pass, self.new_pass,
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
        passed_old = self.old_pass.text().strip()
        passed_new = self.new_pass.text().strip()
        fullname_new = self.full_name.text().strip() if self.full_name.text().strip() else self.user.FullName
        email_new = self.email.text().strip() if self.email.text().strip() else self.user.Email

        print("aaaaa", passed_old, passed_new, fullname_new, email_new)
        editable = False if not passed_old else QApplication.instance().conn.client_checkpassword(self.user.UserID, passed_old)
        
        if not editable:
            QMessageBox.warning(None, "Error", "Password is incorrect!")
            return

        
        if self.new_pass.text().strip():
            if self.new_pass.text().strip() == self.old_pass.text().strip():
                QMessageBox.warning(None, "Error", "New password must be different from old password!")
                return
            QApplication.instance().conn.client_edit(self.user.UserID, fullname_new, email_new, passed_new)
        else:
            QApplication.instance().conn.client_edit(self.user.UserID, fullname_new, email_new)
        QMessageBox.information(None, "Success", "Profile updated successfully!")
        self.refresh_user_data()
        
    def go_back(self):
        if (self.user.Role == "viewer"):
            from src.gui.client_gui import ClientWindow
            self.profile_window = ClientWindow(self.user, self.token)
            self.profile_window.showMaximized()
            self.close()

    def refresh_user_data(self):
        from src.model.Users import User
        data = QApplication.instance().conn.client_profile(self.token)
        new_user = User(data[0], data[1], data[2], data[3], data[4], data[5], data[6], data[7])
        
        self.user = new_user  # cập nhật lại dữ liệu user

        # Cập nhật lại giao diện
        self.username.setText(self.user.Username)
        self.full_name.setText(self.user.FullName)
        self.email.setText(self.user.Email)
        self.created_at.setText(self.user.CreatedAt.strftime("%Y-%m-%d %H:%M:%S") if self.user.CreatedAt else "")
        self.last_login.setText(self.user.LastLogin.strftime("%Y-%m-%d %H:%M:%S") if self.user.LastLogin else "")
        self.role.setText(self.user.Role)

        # Xóa mật khẩu cũ
        self.old_pass.clear()
        self.new_pass.clear()

        print("🔄 Profile refreshed successfully!")


# if __name__ == "__main__":
#     app = QApplication(sys.argv)
#     dummy_user = {"Username": "test_user", "FullName": "Test User", "Email": "test@example.com"}
#     win = ProfileWindow(dummy_user, token="ABC123TOKEN")
#     win.show()
#     sys.exit(app.exec())
