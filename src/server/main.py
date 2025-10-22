import socket
import threading
import struct
import auth
import subprocess

HOST = "0.0.0.0"
PORT = 5000

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

def handle_profile(conn, addr):
    token = read_field(conn).decode("utf-8")
    user = auth.get_user_by_sessionid(token)
    # print(user.FullName)
    send_message(conn, 1, user[0], user[1], user[2], user[3], user[4], user[5], user[6], user[7])
    
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
                reply = handle_profile(conn, addr)
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
