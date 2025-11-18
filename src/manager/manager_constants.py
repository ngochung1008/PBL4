# --- Cấu hình Mạng & Bảo mật ---

# BẮT BUỘC: File CA (Certificate Authority) của server
# Nếu bạn tự tạo cert server (self-signed), file .crt chính là file CA.
# Sao chép file 'server.crt' từ server và đổi tên thành 'ca.crt' ở đây.
import os


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

# --- Lệnh Gửi đi (Manager -> Server) ---
CMD_REGISTER = "register:manager"
CMD_LIST_CLIENTS = "list_clients"
CMD_CONNECT_CLIENT = "connect:"  # Ví dụ: "connect:client_pc_1"
CMD_DISCONNECT = "disconnect"

# --- Lệnh Nhận về (Server -> Manager) ---
CMD_REGISTER_OK = "register_ok"
CMD_CLIENT_LIST_UPDATE = "client_list_update" # "client_list_update:['pc1', 'pc2']"
CMD_SESSION_STARTED = "session_started"
CMD_SESSION_ENDED = "session_ended"
CMD_ERROR = "error"