import socket
import json
import sys


from PyQt6.QtWidgets import QApplication

from src.gui.signin import SignInWindow

SERVER_HOST = "192.168.42.1"  
SERVER_PORT = 5000


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = SignInWindow()
    win.showMaximized()
    sys.exit(app.exec())

def send_request(data):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((SERVER_HOST, SERVER_PORT))
        s.sendall(json.dumps(data).encode("utf-8"))
        resp = s.recv(4096)
        return json.loads(resp.decode("utf-8"))
    except Exception as e:
        print("[ERROR] Cannot connect to server:", e)
        return None
    finally:
        s.close()

def client_login(username, password):
    data = {"type": "login", "username": username, "password": password}
    resp = send_request(data)
    if resp and resp.get("status") == "ok":
        return resp["token"]
    return None

def get_user_by_sessionid(token):
    data = {"type": "get_user", "token": token}
    resp = send_request(data)
    if resp and resp.get("user"):
        return resp["user"]
    return None
