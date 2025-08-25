import socket
import threading
import struct

HOST = '0.0.0.0'  # Lắng nghe trên tất cả IP
PORT = 5000

clients = []  # Danh sách client đang kết nối

def broadcast(data, sender_conn):
    """Gửi dữ liệu cho tất cả client trừ người gửi"""
    for client in clients:
        if client != sender_conn:
            try:
                client.sendall(data)
            except:
                clients.remove(client)

def handle_client(conn, addr):
    print(f"[KẾT NỐI] {addr} đã tham gia phòng chat")
    send_text(conn, "Chào mừng bạn đến phòng chat!")

    while True:
        try:
            header = conn.recv(4)
            if not header:
                break

            data_type = struct.unpack('!I', header)[0]

            if data_type == 1:  # Tin nhắn văn bản
                msg_len_bytes = conn.recv(4)
                if len(msg_len_bytes) < 4:
                    break
                msg_len = struct.unpack('!I', msg_len_bytes)[0]

                msg_data = recv_all(conn, msg_len).decode()
                print(f"{addr}: {msg_data}")

                # Gửi cho người khác
                data = struct.pack('!I', 1) + struct.pack('!I', len(f"{addr}: {msg_data}".encode())) + f"{addr}: {msg_data}".encode()
                broadcast(data, conn)

            elif data_type == 2:  # File
                name_len = struct.unpack('!I', conn.recv(4))[0]
                file_name = recv_all(conn, name_len).decode()
                file_size = struct.unpack('!Q', conn.recv(8))[0]

                file_data = recv_all(conn, file_size)
                print(f"[FILE] {addr} gửi file: {file_name} ({file_size} bytes)")

                # Gửi file cho người khác
                data = (
                    struct.pack('!I', 2) +
                    struct.pack('!I', len(file_name.encode())) +
                    file_name.encode() +
                    struct.pack('!Q', file_size) +
                    file_data
                )
                broadcast(data, conn)

        except Exception as e:
            print(f"[LỖI] {addr}: {e}")
            break

    conn.close()
    if conn in clients:
        clients.remove(conn)
    print(f"[NGẮT KẾT NỐI] {addr} rời phòng chat")
    send_text_all(f"{addr} đã rời phòng chat.", conn)

def recv_all(sock, length):
    """Đọc đủ 'length' byte từ socket"""
    data = b''
    while len(data) < length:
        packet = sock.recv(length - len(data))
        if not packet:
            return data
        data += packet
    return data

def send_text(sock, msg):
    """Gửi tin nhắn text cho 1 client"""
    data = struct.pack('!I', 1) + struct.pack('!I', len(msg.encode())) + msg.encode()
    sock.sendall(data)

def send_text_all(msg, sender_conn=None):
    """Gửi tin nhắn text cho tất cả client"""
    data = struct.pack('!I', 1) + struct.pack('!I', len(msg.encode())) + msg.encode()
    broadcast(data, sender_conn)

def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen(5)
    print(f"[SERVER] Đang lắng nghe tại {HOST}:{PORT}...")

    while True:
        conn, addr = server_socket.accept()
        clients.append(conn)
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    start_server()
