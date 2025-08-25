import socket
import threading
import struct
import os

HOST = '10.10.30.31'
PORT = 5000

def receive_messages(sock):
    """Luồng nhận dữ liệu từ server"""
    while True:
        try:
            # Nhận loại dữ liệu
            header = sock.recv(4)
            if not header:
                break
            data_type = struct.unpack('!I', header)[0]

            if data_type == 1:  # Tin nhắn text
                msg_len = struct.unpack('!I', sock.recv(4))[0]
                msg = sock.recv(msg_len).decode()
                print("\n" + msg)

            elif data_type == 2:  # File
                name_len = struct.unpack('!I', sock.recv(4))[0]
                file_name = sock.recv(name_len).decode()
                file_size = struct.unpack('!Q', sock.recv(8))[0]

                file_data = b''
                while len(file_data) < file_size:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    file_data += chunk

                # Lưu file nhận được
                save_path = "received_" + file_name
                with open(save_path, "wb") as f:
                    f.write(file_data)

                print(f"\n[ĐÃ NHẬN FILE] {file_name} ({file_size} bytes) -> lưu tại {save_path}")

        except Exception as e:
            print("Lỗi khi nhận:", e)
            break

def send_text(sock, msg):
    """Gửi tin nhắn văn bản"""
    data = struct.pack('!I', 1) + struct.pack('!I', len(msg.encode())) + msg.encode()
    sock.sendall(data)

def send_file(sock, file_path):
    """Gửi file"""
    if not os.path.isfile(file_path):
        print("[LỖI] Không tìm thấy file:", file_path)
        return
    file_name = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)

    with open(file_path, "rb") as f:
        file_data = f.read()

    data = (
        struct.pack('!I', 2) +
        struct.pack('!I', len(file_name.encode())) +
        file_name.encode() +
        struct.pack('!Q', file_size) +
        file_data
    )
    sock.sendall(data)
    print(f"[ĐÃ GỬI FILE] {file_name} ({file_size} bytes)")

# Kết nối server
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((HOST, PORT))
print("Kết nối thành công tới server!")

# Luồng nhận tin nhắn/file
threading.Thread(target=receive_messages, args=(client_socket,), daemon=True).start()

# Vòng lặp nhập lệnh
while True:
    msg = input()
    if msg.startswith("/file "):
        # Gửi file: /file đường_dẫn
        path = msg[6:].strip()
        send_file(client_socket, path)
    else:
        send_text(client_socket, msg)