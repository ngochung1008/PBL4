import socket
import struct
from config import server_config
from src.model.Users import User
import json
from datetime import datetime

HOST = server_config.SERVER_IP   # IP của server (chạy local thì giữ nguyên)
PORT = server_config.SERVER_HOST  # port server lắng nghe

# HOST = "10.10.31.61"
# PORT = 5000

def send_message(conn, msg_type, *fields):
    print("send")
    parts = []
    parts.append(struct.pack("!B", msg_type))  # 1 byte msg_type
    for field in fields:
        if isinstance(field, str):
            field = field.encode("utf-8")  # chuyển str -> bytes
        parts.append(struct.pack("!I", len(field)))  # 4 byte độ dài
        parts.append(field)  # nội dung
    conn.sendall(b"".join(parts))
    print("send xong")

def recv_exact(conn, n):
    data = b""
    while len(data) < n:
        chunk = conn.recv(n - len(data))
        if not chunk:
            raise ConnectionError("Mat ket noi server")
        data += chunk
    return data

def read_field(conn):
    """Đọc 1 field: [len(4B)][data]"""
    (length,) = struct.unpack("!I", recv_exact(conn, 4))
    data = recv_exact(conn, length)
    return data

def handle_login(conn):
    username = read_field(conn).decode("utf-8")
    return f"Hello {username}".encode("utf-8")

def client_login(username, password):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        print(f"[+] Ket noi toi server {HOST}:{PORT}")

        send_message(s, 1, username, password)
        print("[>] Da gui yeu cau dang nhap")

        reply = s.recv(1)
        reply = struct.unpack("!B", reply)[0]

        if (reply == 1):
            token = read_field(s).decode("utf-8")
            print("[<] Dang nhap thanh cong"+token)
            return token
        else:
            print("[<] Dang nhap that bai")
            return None

def try_parse_datetime(value):
    """Thử parse chuỗi ISO thành datetime, nếu không được thì trả lại nguyên"""
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return value
    return value

def convert_datetimes(obj):
    """Đệ quy chuyển tất cả chuỗi ISO trong dict/list về datetime"""
    if isinstance(obj, dict):
        return {k: convert_datetimes(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_datetimes(v) for v in obj]
    else:
        return try_parse_datetime(obj)

def client_profile(token):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        print(f"[+] Ket noi toi server {HOST}:{PORT}")

        send_message(s, 2, token)

        reply = s.recv(1)
        reply = struct.unpack("!B", reply)[0]

        print("Nhan duoc user")
        
        if (reply == 1):
            length_data = s.recv(4)
            if not length_data:
                return None, None
            length = struct.unpack("!I", length_data)[0]

            # Bước 3: đọc phần nội dung JSON
            json_data = b""
            while len(json_data) < length:
                chunk = s.recv(length - len(json_data))
                if not chunk:
                    break
                json_data += chunk

            # Bước 4: giải mã JSON
            data = json.loads(json_data.decode("utf-8"))
            data = convert_datetimes(data)
            print(data)
            return data
        else:
            print("[<] Dang nhap that bai")
            return None

def client_logout(token):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        print(f"[+] Ket noi toi server {HOST}:{PORT}")

        send_message(s, 3, token)

def client_signup(username, password, fullname, email):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        print(f"[+] Ket noi toi server {HOST}:{PORT}")

        send_message(s, 4, username, password, fullname, email)

        reply = s.recv(1)
        reply = struct.unpack("!B", reply)[0]
        
        if (reply == 1):
            return True
        else:
            print("[<] Dang ky that bai")
            return False
        
def client_checkpassword(userid, password):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        print(f"[+] Ket noi toi server {HOST}:{PORT}")

        send_message(s, 5, userid, password)

        reply = s.recv(1)
        reply = struct.unpack("!B", reply)[0]
        
        if (reply == 1):
            return True
        else:
            print("[<] Kiem tra mat khau that bai")
            return False

def client_edit(userid, fullname, email, new_password=""):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        print(f"[+] Ket noi toi server {HOST}:{PORT}")

        send_message(s, 6, userid, fullname, email, new_password)

        reply = s.recv(1)
        reply = struct.unpack("!B", reply)[0]
        
        if (reply == 1):
            return True
        else:
            print("[<] Cap nhat mat khau that bai")
            return False
        
# user = input("Username: ")
# pw = input("Password: ")

# # if not reply:
# #     print("[!] Server Khong tra loi")
# #     return

# print("[<] Phan hoi tu server:", reply)
