# config.py

# --- Thiết lập mạng ---
SERVER_HOST = "10.248.230.77"  # Địa chỉ IP của server

CONTROL_PORT = 9010         # Cổng giao tiếp lệnh Manager <-> Server
CLIENT_PORT = 9011          # Cổng giao tiếp lệnh Server -> Client
SCREEN_PORT = 5000          # Cổng giao tiếp stream màn hình Client -> Server

# --- Thiết lập Stream ---
FPS = 15                    # Tốc độ khung hình/giây
QUALITY = 70                # Chất lượng nén JPEG (1-100)

# --- Anti-Feedback Loop (Latency) Settings ---
# Thời gian Manager bỏ qua input cục bộ sau khi nhận lệnh di chuyển từ Client (ManagerViewer.show_remote_cursor)
MANAGER_IGNORE_DURATION_S = 0.4 

# Thời gian Client tạm dừng gửi cursor_update sau khi nhận lệnh di chuyển từ Manager (ClientController.handle_mouse)
CLIENT_SUPPRESS_DURATION_S = 0.4