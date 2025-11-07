import socket
import os
import threading
from src.client.file_transfer.database import Database
from config import server_config

db = Database()
MAX_FILE_SIZE = 20 * 1024 * 1024   # 20MB

def receive_file(sock):
    while True:
        header = sock.recv(1024).decode()
        if not header:
            break

        parts = header.split("|")
        if len(parts) != 4:
            continue

        command, sender, filename, filesize = parts
        filesize = int(filesize)

        os.makedirs("log", exist_ok=True)
        save_path = f"log/{filename}"

        received = 0
        with open(save_path, "wb") as f:
            while received < filesize:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                f.write(chunk)
                received += len(chunk)

        print(f"\n✅ Nhận file {save_path}")


def start_client():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((server_config.SERVER_IP, 9999))

    client_id = sock.recv(1024).decode()
    print(f"Connected. Your ID = {client_id}")

    threading.Thread(target=receive_file, args=(sock,), daemon=True).start()

    while True:
        cmd = input("\nSEND <client1,client2,..> <filepath> : ")

        if not cmd.startswith("SEND"):
            print("Sai cú pháp")
            continue

        try:
            _, target_ids, filepath = cmd.split(" ")
        except:
            print("Sai cú pháp")
            continue

        if not os.path.exists(filepath):
            print("❌ File không tồn tại")
            continue

        filesize = os.path.getsize(filepath)
        if filesize > MAX_FILE_SIZE:
            print("❌ File quá lớn!")
            continue

        filename = os.path.basename(filepath)
        header = f"SEND_FILE|{target_ids}|{filename}|{filesize}"

        sock.send(header.encode())

        with open(filepath, "rb") as f:
            sock.send(f.read())

        print("✅ Đã gửi file.")

        # log upload
        db.log_transfer(filename, filesize, "UPLOAD")


if __name__ == "__main__":
    start_client()
