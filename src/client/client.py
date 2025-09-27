import threading
from client_input import ClientInput
from client_screen import ClientScreen

SERVER_HOST = "10.10.30.179"
INPUT_PORT = 9012
SCREEN_PORT = 5000
FPS = 1  # khung hình/giây

if __name__ == "__main__":
    # chạy input listener ở luồng riêng
    input_handler = ClientInput(SERVER_HOST, INPUT_PORT)
    threading.Thread(target=input_handler.run, daemon=True).start()

    # chạy screen streamer (blocking)
    screen_handler = ClientScreen(SERVER_HOST, SCREEN_PORT, FPS)
    screen_handler.run()
