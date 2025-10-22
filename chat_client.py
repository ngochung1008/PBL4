import socket
import json
import sys


from PyQt6.QtWidgets import QApplication

from src.gui.signin import SignInWindow
from src.server.auth import get_user_by_sessionid, sign_in
from src.client.auth import client_profile, client_login
import mysql.connector

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
    win = SignInWindow()
    win.showMaximized()
    sys.exit(app.exec())
    # client_login("admin", "admin")
    # client_profile("d3e6d5c2-ab5d-11f0-87af-005056c00001")
