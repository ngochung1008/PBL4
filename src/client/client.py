# client.py

import threading
import time
from client_controller import ClientController
from client_screen import ClientScreen
import sys
import config

SERVER_HOST = config.SERVER_HOST
CONTROL_PORT = config.CONTROL_PORT
CLIENT_PORT = config.CLIENT_PORT
SCREEN_PORT = config.SCREEN_PORT
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
    
    # Gửi handler vào một thread và giữ luồng chính (main) mở
    threading.Thread(target=screen_streamer_loop, args=(screen_handler,), daemon=True).start()
    
    # GIỮ LUỒNG CHÍNH MỞ: để các luồng daemon tiếp tục chạy
    while True:
        time.sleep(1)