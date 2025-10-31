import socket
import struct
import json
from datetime import datetime
from config import server_config

class ClientConnection:
    def __init__(self):
        self.host = server_config.SERVER_IP
        self.port = server_config.SERVER_HOST
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))
        print(f"[+] Kết nối tới server {self.host}:{self.port}")

    # ----------------- Tiện ích -----------------
    def send_message(self, msg_type, *fields):
        parts = [struct.pack("!B", msg_type)]
        for field in fields:
            if isinstance(field, str):
                field = field.encode("utf-8")
            parts.append(struct.pack("!I", len(field)))
            parts.append(field)
        self.sock.sendall(b"".join(parts))

    def recv_exact(self, n):
        data = b""
        while len(data) < n:
            chunk = self.sock.recv(n - len(data))
            if not chunk:
                raise ConnectionError("Mất kết nối với server")
            data += chunk
        return data

    def read_field(self):
        (length,) = struct.unpack("!I", self.recv_exact(4))
        return self.recv_exact(length)

    # ----------------- Các API -----------------
    def client_login(self, username, password):
        self.send_message(1, username, password)
        reply = struct.unpack("!B", self.recv_exact(1))[0]
        if reply == 1:
            token = self.read_field().decode("utf-8")
            print("[<] Đăng nhập thành công:", token)
            return token
        print("[<] Đăng nhập thất bại")
        return None

    def client_profile(self, token):
        self.send_message(2, token)
        reply = struct.unpack("!B", self.recv_exact(1))[0]
        if reply != 1:
            print("[<] Lấy profile thất bại")
            return None

        (length,) = struct.unpack("!I", self.recv_exact(4))
        json_data = self.recv_exact(length)
        data = json.loads(json_data.decode("utf-8"))
        return self.convert_datetimes(data)

    def client_logout(self, token):
        self.send_message(3, token)
        print("[>] Đã gửi yêu cầu logout")

    def client_signup(self, username, password, fullname, email):
        self.send_message(4, username, password, fullname, email)
        reply = struct.unpack("!B", self.recv_exact(1))[0]
        return reply == 1

    def client_checkpassword(self, userid, password):
        self.send_message(5, userid, password)
        reply = struct.unpack("!B", self.recv_exact(1))[0]
        return reply == 1

    def client_edit(self, userid, fullname, email, new_password=""):
        self.send_message(6, userid, fullname, email, new_password)
        reply = struct.unpack("!B", self.recv_exact(1))[0]
        return reply == 1

    def client_check(self, username):
        self.send_message(7, username)
        reply = struct.unpack("!B", self.recv_exact(1))[0]
        if reply == 1:
            print("[<] Username tồn tại")
            token = self.read_field().decode("utf-8")
            return True, token
        print("[<] Username không tồn tại")
        return False, None
    
    # ----------------- Xử lý thời gian -----------------
    def try_parse_datetime(self, value):
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                return value
        return value

    def convert_datetimes(self, obj):
        if isinstance(obj, dict):
            return {k: self.convert_datetimes(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self.convert_datetimes(v) for v in obj]
        else:
            return self.try_parse_datetime(obj)

    # ----------------- Đóng kết nối -----------------
    def close(self):
        self.sock.close()
        print("[x] Đã đóng kết nối với server")