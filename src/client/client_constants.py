# --- Cấu hình Mạng & Bảo mật ---

# ID của client, server sẽ thấy tên này.
# Dùng socket.gethostname() để lấy tên máy tự động.
import os
import socket
try:
    CLIENT_ID = socket.gethostname()
except:
    CLIENT_ID = "default_client"

# BẮT BUỘC: File CA (Certificate Authority) của server
# Sao chép file 'server.crt' từ server và đổi tên thành 'ca.crt' ở đây.
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
CA_FILE = os.path.join(_CURRENT_DIR, "ca.crt")


# --- Định nghĩa Kênh (Channel) ---
# Phải khớp với server
CHANNEL_VIDEO = 2
CHANNEL_CONTROL = 3
CHANNEL_INPUT = 4
CHANNEL_FILE = 5

ALL_CHANNELS = (
    CHANNEL_VIDEO,
    CHANNEL_CONTROL,
    CHANNEL_INPUT,
    CHANNEL_FILE,
)

# --- Lệnh Gửi đi (Client -> Server) ---
CMD_REGISTER = f"register:client"
CMD_DISCONNECT = "disconnect"