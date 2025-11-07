import socket
import threading
from src.client.file_transfer.database import Database

clients = {}          # client_id : socket
db = Database()
MAX_FILE_SIZE = 20 * 1024 * 1024   # 20MB

def forward_file(sender_sock, target_sock, header, filesize, filename):

    target_sock.send(header.encode())

    received = 0
    while received < filesize:
        chunk = sender_sock.recv(4096)
        if not chunk:
            break
        target_sock.send(chunk)
        received += len(chunk)

    # lưu vào database: upload
    db.log_transfer(filename, filesize, "UPLOAD")


def client_handler(client_sock, client_id):
    while True:
        try:
            header = client_sock.recv(1024).decode()
        except:
            break

        if not header:
            break

        parts = header.split("|")
        if len(parts) != 4:
            continue

        command, targets, filename, filesize = parts
        filesize = int(filesize)

        # kiểm tra kích thước file
        if filesize > MAX_FILE_SIZE:
            client_sock.send(b"ERROR|File too large")
            continue

        if command == "SEND_FILE":
            list_targets = targets.split(",")

            for tid in list_targets:
                if tid in clients:
                    forward_file(client_sock, clients[tid], header, filesize, filename)
                else:
                    client_sock.send(f"ERROR|Target {tid} not found".encode())


def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("0.0.0.0", 9999))
    server.listen()
    print("SERVER RUNNING ON PORT 9999")

    idx = 1
    while True:
        client_sock, addr = server.accept()
        client_id = f"CLIENT_{idx}"
        idx += 1

        clients[client_id] = client_sock
        client_sock.send(client_id.encode())

        print(f"{client_id} connected")

        threading.Thread(target=client_handler, args=(client_sock, client_id), daemon=True).start()


if __name__ == "__main__":
    start_server()
