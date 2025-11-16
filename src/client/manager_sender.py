# manager_sender.py
import socket
import threading
import time
import json

class ManagerSender:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = None
        self.lock = threading.Lock()
        self.connected = False

    def connect(self):
        self.sock = socket.create_connection((self.host, self.port), timeout=10)
        self.sock.sendall(b"MANAGER\n")
        self.connected = True
        threading.Thread(target=self._keepalive, daemon=True).start()

    def _keepalive(self):
        while self.connected:
            time.sleep(30)
            try:
                self.send({"type": "PING"})
            except:
                self.connected = False

    def send(self, data):
        if not self.connected:
            raise RuntimeError("Not connected")
        with self.lock:
            msg = (json.dumps(data) + "\n").encode("utf-8")
            self.sock.sendall(msg)

    def send_input(self, input_obj):
        self.send(input_obj)

    def close(self):
        self.connected = False
        try: self.sock.close()
        except: pass
