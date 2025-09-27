import threading
import socket
from manager_input import ManagerInput
from manager_viewer import ManagerViewer

SERVER_HOST = "10.10.30.179"
INPUT_PORT = 9012
SCREEN_PORT = 5000

if __name__ == "__main__":
    # Kết nối input
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((SERVER_HOST, INPUT_PORT))
    sock.listen(1)
    print("[MANAGER] Waiting for client input connection...")
    conn, addr = sock.accept()
    print("[MANAGER] Client input connected:", addr)

    # Input handler
    input_handler = ManagerInput(conn)
    threading.Thread(target=input_handler.run, daemon=True).start()

    # Viewer handler
    viewer = ManagerViewer(SERVER_HOST, SCREEN_PORT)
    viewer.run()