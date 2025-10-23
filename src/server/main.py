import socket
import threading
import struct
import auth
import subprocess
import json
from datetime import datetime

HOST = "0.0.0.0"
PORT = 5000

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

def send_json(conn, msg_type, data):
    json_data = json.dumps(data, cls=DateTimeEncoder).encode("utf-8")
    # json_data = json.dumps(data).encode("utf-8")
    length = struct.pack("!I", len(json_data))
    header = struct.pack("!B", msg_type)
    conn.sendall(header + length + json_data)
        
def send_message(conn, msg_type, *fields):
    parts = []
    header = struct.pack("!B", msg_type)
    parts.append(header)

    for i, field in enumerate(fields):
        print(f"DEBUG field[{i}] =", repr(field), type(field))
        if field is None:
            continue
        if isinstance(field, str):
            field = field.encode("utf-8")
        elif not isinstance(field, (bytes, bytearray)):
            raise TypeError(f"Field {i} must be str or bytes, got {type(field)}")

        parts.append(struct.pack("!I", len(field)))
        parts.append(field)

    data = b"".join(parts)
    print("DEBUG final data:", data)
    conn.sendall(data)

def recv_exact(conn, n):
    """Đọc đúng n byte từ socket"""
    data = b""
    while len(data) < n:
        chunk = conn.recv(n - len(data))
        if not chunk:
            raise ConnectionError("Lost connection")
        data += chunk
    return data
  
def read_field(conn):
    """Đọc 1 field: [len(4B)][data]"""
    (length,) = struct.unpack("!I", recv_exact(conn, 4))
    data = recv_exact(conn, length)
    return data

def get_mac_from_ip(ip):
    try:
        # chạy lệnh arp để lấy MAC (chỉ hoạt động nếu client cùng mạng LAN)
        output = subprocess.check_output(f"arp -a {ip}", shell=True).decode()
        for line in output.splitlines():
            if ip in line:
                # lấy MAC trong dòng chứa ip
                return line.split()[1].replace("-", ":")
    except Exception:
        pass
    return None

def handle_login(conn, addr):
    username = read_field(conn).decode("utf-8")
    password = read_field(conn).decode("utf-8")
    print(f"[LOGIN] {username}:{password}")
    check = auth.sign_in(username, password)
    print(f"[LOGIN] {username} ket qua: {check}")
    if  (check == False):
        send_message(conn, 0)
    else:
        token = auth.create_session(username, addr[0], get_mac_from_ip(addr[0]))
        print(f"[TOKEN] {token}")
        send_message(conn, 1, token)

def handle_profile(conn):
    token = read_field(conn).decode("utf-8")
    user = auth.get_user_by_sessionid(token)
    print("[PROFILE] User:", user)

    send_json(conn, 1, user)

def handle_logout(conn):
    token = read_field(conn).decode("utf-8")
    user = auth.log_out(token)

    send_json(conn, 1, user)

def handle_signup(conn):
    username = read_field(conn).decode("utf-8")
    password = read_field(conn).decode("utf-8")
    fullname = read_field(conn).decode("utf-8")
    email = read_field(conn).decode("utf-8")
    print(f"[SIGNUP] {username}:{password}:{fullname}:{email}")
    check = auth.sign_up(username, password, fullname, email)
    print(f"[SIGNUP] {username} ket qua: {check}")
    if  (check == False):
        send_message(conn, 0)
    else:
        send_message(conn, 1)

def client_checkpassword(conn):
    userid = read_field(conn).decode("utf-8")
    password = read_field(conn).decode("utf-8")
    print(f"[CHECKPASSWORD] {userid}:{password}")
    check = auth.check_pasword(userid, password)
    print(f"[CHECKPASSWORD] {userid} ket qua: {check}")
    if  (check == False):
        send_message(conn, 0)
    else:
        send_message(conn, 1)

def client_edit(conn):
    userid = read_field(conn).decode("utf-8")
    fullname = read_field(conn).decode("utf-8")
    email = read_field(conn).decode("utf-8")
    new_password = read_field(conn).decode("utf-8")
    print(f"[EDIT] {userid}:{fullname}:{email}:{new_password}")
    check = auth.edit_user(userid, fullname, email, new_password)
    print(f"[EDIT] {userid} ket qua: {check}")
    if  (check == False):
        send_message(conn, 0)
    else:
        send_message(conn, 1)
        
def handle_file(conn):
    filename = read_field(conn).decode("utf-8")
    (file_len,) = struct.unpack("!I", recv_exact(conn, 4))  # độ dài file
    received = 0
    with open("recv_" + filename, "wb") as f:
        while received < file_len:
            chunk = conn.recv(min(4096, file_len - received))
            if not chunk:
                raise ConnectionError("Lost connection during file transfer")
            f.write(chunk)
            received += len(chunk)
    print(f"[FILE] was saved recv_{filename} ({file_len} bytes)")
    return f"Received file {filename}".encode("utf-8")

def client_thread(conn, addr):
    print(f"[+] Connect from {addr}")
    try:
        while True:
            header = conn.recv(1)  # chỉ 1 byte: msg_type
            if not header:
                break
            print(header)
            msg_type = struct.unpack("!B", header)[0]
            print(msg_type)
            if msg_type == 1:
                print(f"[{addr}] Login request")
                handle_login(conn, addr)
            elif msg_type == 2:
                print("ok")
                handle_profile(conn)
            elif msg_type == 3:
                print(f"[{addr}] Logout request")
                handle_logout(conn)
            elif msg_type == 4:
                print(f"[{addr}] Signup request")
                handle_signup(conn)
            elif msg_type == 5:
                print(f"[{addr}] Check password request")
                client_checkpassword(conn)
            elif msg_type == 6:
                print(f"[{addr}] Edit user request")
                client_edit(conn)
            else:
                print("NO")
                reply = b"Unknown type"

            # conn.sendall(reply)

    except Exception as e:
        print(f"Error {addr}: {e}")
    finally:
        conn.close()
        print(f"[-] Interrupt {addr}")

def start_server():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((HOST, PORT))
    s.listen()
    print(f"[*] Server run {HOST}:{PORT}")
    while True:
        conn, addr = s.accept()
        threading.Thread(target=client_thread, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    # print(auth.get_user_by_sessionid("d3e6d5c2-ab5d-11f0-87af-005056c00001"))
    start_server()
