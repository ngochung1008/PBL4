import socket
import json
import sys


from PyQt6.QtWidgets import QApplication

from src.gui.signin import SignInWindow

def on_app_exit():
    print("⏳ Ứng dụng chuẩn bị thoát, cập nhật LastLogin...")
    if QApplication.instance().current_user is None:
        return
    from src.client.auth import client_logout
    client_logout(QApplication.instance().current_user)
    print("✅ Đã cập nhật LastLogin.")

if __name__ == "__main__":
    # print("Connecting to DB...")
    # conn = mysql.connector.connect(
    #     host="localhost",       # Địa chỉ server MySQL (vd: "127.0.0.1")
    #     user="root",            # Tài khoản MySQL
    #     password="root",# Mật khẩu MySQL
    #     database="pbl4"       # Tên database muốn dùng
    # )
    # print("✅ Connected to DB")

    # print(sign_in("admin", "admin12"))
    # print(get_user_by_sessionid("d3e6d5c2-ab5d-11f0-87af-005056c00001"))
    app = QApplication(sys.argv)
    app.current_user = None  # lưu thông tin user hiện tại
    app.aboutToQuit.connect(on_app_exit)
    win = SignInWindow()
    win.show()
    sys.exit(app.exec())
    # client_login("admin", "admin")
    # client_profile("d3e6d5c2-ab5d-11f0-87af-005056c00001")
