# client.py

import threading
from client_controller import ClientController
from client_screen import ClientScreen

<<<<<<< HEAD
SERVER_HOST = "10.169.157.77"
CONTROL_PORT = 9010  
CLIENT_PORT = 9011    
SCREEN_PORT = 5000  
FPS = 1 
=======
SERVER_HOST = "10.10.30.141"
CONTROL_PORT = 9010   # Manager -> Server (chỉ Manager dùng)
CLIENT_PORT = 9011    # Client nhận input từ Server
SCREEN_PORT = 5000    # gửi màn hình tới server
FPS = 1  # khung hình/giây
>>>>>>> 240af18aa9c1449a1ddad62f292834cc5f272e05

if __name__ == "__main__":
    # chạy input controller ở luồng riêng (nhận từ SERVER -> CLIENT)
    controller = ClientController(SERVER_HOST, CLIENT_PORT)   # sửa lại thành CLIENT_PORT
    threading.Thread(target=controller.run, daemon=True).start()

    # chạy screen streamer (blocking)
    screen_handler = ClientScreen(SERVER_HOST, SCREEN_PORT, FPS)
    screen_handler.run()