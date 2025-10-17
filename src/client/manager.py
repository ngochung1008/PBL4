# manager.py

import threading
import socket
import sys
from PyQt6.QtWidgets import QApplication
from manager_input import ManagerInput
from manager_viewer import ManagerViewer

SERVER_HOST = "10.20.2.222"
CONTROL_PORT = 9010   # gửi input tới server
SCREEN_PORT = 5000    # nhận màn hình từ server

if __name__ == "__main__":
    # Khởi tạo QApplication trước
    app = QApplication(sys.argv)

    # Viewer handler (nhận màn hình từ server) - tạo trước để truyền vào input handler
    viewer = ManagerViewer(SERVER_HOST, SCREEN_PORT)
    viewer.show()

    # Kết nối tới server để gửi input
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((SERVER_HOST, CONTROL_PORT))
    print("[MANAGER] Connected to server for input")

    # Input handler (gửi sự kiện bàn phím/chuột) - truyền viewer để dùng scale nếu cần
    input_handler = ManagerInput(sock, viewer=viewer)
    threading.Thread(target=input_handler.run, daemon=True).start()

    sys.exit(app.exec())