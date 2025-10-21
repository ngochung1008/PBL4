# client.py

import threading
from time import time
from client_controller import ClientController
from client_screen import ClientScreen
import sys

SERVER_HOST = "10.10.26.93"
CONTROL_PORT = 9010   # Manager -> Server 
CLIENT_PORT = 9011    # Client nhận input từ Server
SCREEN_PORT = 5000    # Gửi màn hình tới server
FPS = 15  # Tốc độ khung hình/giây

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