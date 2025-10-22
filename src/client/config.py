# config.py

# --- Thiết lập mạng ---
SERVER_HOST = "10.248.230.77"  # Địa chỉ IP của server

CONTROL_PORT = 9010         # Cổng giao tiếp lệnh Manager <-> Server
CLIENT_PORT = 9011          # Cổng giao tiếp lệnh Server -> Client
SCREEN_PORT = 5000          # Cổng giao tiếp stream màn hình Client -> Server

# --- Thiết lập Stream ---
FPS = 15                    # Tốc độ khung hình/giây
QUALITY = 70                # Chất lượng nén JPEG (1-100)