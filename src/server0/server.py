# server0/server.py

from server0.server_network.server_app import ServerApp
from server0.server_constants import SERVER_HOST, SERVER_PORT, CERT_FILE, KEY_FILE
import signal
import time
import os
import sys

app = None

def main():
    global app
    
    # --- Kiểm tra Cert/Key trước khi khởi động ---
    if not os.path.exists(CERT_FILE) or not os.path.exists(KEY_FILE):
        print(f"Lỗi: Không tìm thấy file SSL certificate hoặc key.")
        print(f"Vui lòng tạo '{CERT_FILE}' và '{KEY_FILE}' đặt cùng thư mục.")
        print("Bạn có thể dùng lệnh (cho development):")
        print("openssl req -x509 -newkey rsa:2048 -keyout server.key -out server.crt -sha256 -days 365 -nodes")
        sys.exit(1)
        
    print("Khởi động Server...")
    app = ServerApp(
        host=SERVER_HOST, 
        port=SERVER_PORT,
        certfile=CERT_FILE,
        keyfile=KEY_FILE
    )
    app.start()

    def _term(signum, frame):
        print("\nĐang tắt Server...")
        if app:
            app.stop()
        print("Server đã tắt.")
        sys.exit(0)

    signal.signal(signal.SIGINT, _term)
    signal.signal(signal.SIGTERM, _term)

    # Giữ luồng chính hoạt động
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        _term(None, None)

if __name__ == "__main__":
    main()