# key_client.py
import socket
import keyboard
from datetime import datetime

SERVER_IP = '10.10.30.251' # Đổi IP nếu chạy khác máy
PORT = 5000

def start_client():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((SERVER_IP, PORT))
    print(f"🔗 Đã kết nối tới server {SERVER_IP}:{PORT}")
    print("⌨️ Nhấn phím bất kỳ để gửi... (Nhấn ESC để thoát)")

    try:
        while True:
            event = keyboard.read_event(suppress=False)
            if event.event_type == keyboard.KEY_DOWN:
                key = event.name
                current_time = datetime.now().strftime("%H:%M:%S")
                print(f"[{current_time}] Gửi phím: {key}")
                client_socket.sendall(key.encode('utf-8'))

                if key == 'esc':
                    print("🚪 Đã thoát.")
                    break

    except KeyboardInterrupt:
        print("\n🛑 Ngắt kết nối.")
    finally:
        client_socket.close()

if __name__ == "__main__":
    start_client()
