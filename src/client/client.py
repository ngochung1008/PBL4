# client.py

import threading
import time
from datetime import datetime
from client_controller import ClientController
from client_screen import ClientScreen
from transfer_channel import TransferChannel
from client_transfer import ClientTransfer
import sys
import config

SERVER_HOST = config.SERVER_HOST
CONTROL_PORT = config.CONTROL_PORT
CLIENT_PORT = config.CLIENT_PORT
SCREEN_PORT = config.SCREEN_PORT
TRANSFER_PORT = config.TRANSFER_PORT
FPS = config.FPS

# Vòng lặp chạy ClientScreen.run() - sẽ chặn luồng này
def screen_streamer_loop(handler):
    try:
        handler.run()
    except Exception as e:
        print(f"[CLIENT] Screen handler stopped: {e}")
    finally:
        # Nếu luồng screen dừng, đóng toàn bộ chương trình Client
        print("[CLIENT] Screen streaming terminated. Shutting down application.")
        import os; os._exit(0) # Thoát hẳn chương trình Client

# Vòng lặp chạy ClientController.run() - sẽ chặn luồng này
def controller_loop(controller):
    try:
        controller.run()
    except Exception as e:
        print(f"[CLIENT] Controller handler stopped: {e}")
    finally:
        # Nếu luồng controller dừng, đóng toàn bộ chương trình Client
        print("[CLIENT] Controller terminated. Shutting down application.")
        import os; os._exit(0) # Thoát hẳn chương trình Client

if __name__ == "__main__":
    username = "client1"

    # 1. Định nghĩa callback để xử lý gói nhận
    def handle_transfer_package(pkg):
        pkg_type = pkg.get("type")
        sender = pkg.get("sender")
        data = pkg.get("data")

        if pkg_type == "chat":
            print(f"[CHAT] {sender} said: {data}")
        elif pkg_type == "file_meta":
            print(f"[FILE] Receiving file metadata from {sender}: {data['filename']}")

    # 2. Khởi tạo và kết nối TransferChannel (Cần chạy trước Controller)
    transfer_channel = TransferChannel(SERVER_HOST, TRANSFER_PORT, handle_transfer_package)
    if not transfer_channel.connect():
        print("[CLIENT] Could not connect to transfer server.")
        sys.exit(1)
        
    # 3. Khởi tạo ClientTransfer (Cho file data/meta)
    client_transfer = ClientTransfer(SERVER_HOST, TRANSFER_PORT, username)
    client_transfer.start()

    # 4. Khởi tạo luồng Input Controller (truyền kênh Transfer vào)
    controller = ClientController(SERVER_HOST, CLIENT_PORT, username, transfer_channel=transfer_channel) 
    threading.Thread(target=controller_loop, args=(controller,), daemon=True).start()

    # 5. Khởi tạo luồng Screen Streamer 
    screen_handler = ClientScreen(SERVER_HOST, SCREEN_PORT, FPS)
    threading.Thread(target=screen_streamer_loop, args=(screen_handler,), daemon=True).start()

    # GIỮ LUỒNG CHÍNH MỞ
    while True:
        time.sleep(1)