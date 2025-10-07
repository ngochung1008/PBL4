# manager.py

import threading
import socket
from manager_input import ManagerInput
from manager_viewer import ManagerViewer

SERVER_HOST = "10.169.157.77"
CONTROL_PORT = 9010   # gửi input tới server
SCREEN_PORT = 5000    # nhận màn hình từ server

if __name__ == "__main__":
    # Kết nối tới server để gửi input
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((SERVER_HOST, CONTROL_PORT))
    print("[MANAGER] Connected to server for input")

    # Input handler (gửi sự kiện bàn phím/chuột)
    input_handler = ManagerInput(sock)
    threading.Thread(target=input_handler.run, daemon=True).start()

    # Viewer handler (nhận màn hình từ server)
    viewer = ManagerViewer(SERVER_HOST, SCREEN_PORT)
    viewer.run()