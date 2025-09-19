# manager.py
import socket

SERVER_HOST = "127.0.0.1"   # IP server
SERVER_PORT = 9010          # cổng dành cho Manager

def main():
    with socket.create_connection((SERVER_HOST, SERVER_PORT)) as s:
        print("Connected to server. Enter commands:")
        while True:
            cmd = input("> ")
            if cmd.lower() == "exit":
                break
            s.sendall(cmd.encode("utf-8"))

if __name__ == "__main__":
    main()