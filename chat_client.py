import socket
import json
import sys


from PyQt6.QtWidgets import QApplication

from src.gui.signin import SignInWindow

def on_app_exit():
    print("⏳ Ứng dụng chuẩn bị thoát, cập nhật LastLogin...")
    if QApplication.instance().current_user is None:
        return
    QApplication.instance().conn.client_logout(QApplication.instance().current_user)
    print("✅ Đã cập nhật LastLogin.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    from src.client.auth import ClientConnection
    app.conn = ClientConnection()
    app.client_connected = []
    app.client_list = []
    app.current_user = None  
    app.current_name = None
    app.aboutToQuit.connect(on_app_exit)
    win = SignInWindow()
    win.show()
    sys.exit(app.exec())
