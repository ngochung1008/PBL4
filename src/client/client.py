# client.py

import threading
import time
from client_controller import ClientController
from client_screen import ClientScreen
from transfer_channel import TransferChannel
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
    # Khởi tạo luồng Input Controller (nhận lệnh từ SERVER -> CLIENT)
    controller = ClientController(SERVER_HOST, CLIENT_PORT)
    threading.Thread(target=controller_loop, args=(controller,), daemon=True).start()

    # Khởi tạo luồng Screen Streamer (gửi frame từ CLIENT -> SERVER)
    screen_handler = ClientScreen(SERVER_HOST, SCREEN_PORT, FPS)

    # 1. Định nghĩa callback để xử lý gói nhận
    def handle_transfer_package(pkg):
        pkg_type = pkg.get("type")
        sender = pkg.get("sender")
        data = pkg.get("data")

        if pkg_type == "chat":
            print(f"[CHAT] {sender} said: {data}")
            # Hiển thị tin nhắn chat trên Client
        elif pkg_type == "file_meta":
            # Bắt đầu nhận file (tên file, kích thước)
            print(f"[FILE] Receiving file metadata from {sender}: {data['filename']}")
            # Chuẩn bị luồng/lớp để nhận dữ liệu file
        # ... (thêm logic xử lý file data) ...

    # 2. Khởi tạo và kết nối TransferChannel
    transfer_channel = TransferChannel(SERVER_HOST, TRANSFER_PORT, handle_transfer_package)
    if not transfer_channel.connect():
        print("[CLIENT] Could not connect to transfer server.")
        # Xử lý lỗi nếu cần
    
    # Gửi handler vào một thread và giữ luồng chính (main) mở
    threading.Thread(target=screen_streamer_loop, args=(screen_handler,), daemon=True).start()
    
    # GIỮ LUỒNG CHÍNH MỞ: để các luồng daemon tiếp tục chạy
    while True:
        time.sleep(1)