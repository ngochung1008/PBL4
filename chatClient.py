import socket
import struct

HOST = "10.10.30.15"   # IP của server (chạy local thì giữ nguyên)
PORT = 5000

def send_message(conn, msg_type, *fields):
    parts = []
    parts.append(struct.pack("!B", msg_type))  # 1 byte msg_type
    for field in fields:
        if isinstance(field, str):
            field = field.encode("utf-8")  # chuyển str -> bytes
        parts.append(struct.pack("!I", len(field)))  # 4 byte độ dài
        parts.append(field)  # nội dung
    conn.sendall(b"".join(parts))

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

        # while True:
            # gửi tín hiệu đăng nhập: msg_type = 1
        send_message(s, 1, username, password)
        print("[>] Da gui yeu cau dang nhap")

        # nhận phản hồi
        reply = s.recv(1)
        reply = struct.unpack("!B", reply)[0]

        if (reply == 1):
            token = read_field(s).decode("utf-8")
            print("[<] Dang nhap thanh cong"+token)
        else:
            print("[<] Dang nhap that bai")
        
        # user = input("Username: ")
        # pw = input("Password: ")

        # # if not reply:
        # #     print("[!] Server Khong tra loi")
        # #     return

        # print("[<] Phan hoi tu server:", reply)

if __name__ == "__main__":
    user = input("Username: ")
    pw = input("Password: ")
    client_login(user, pw)
