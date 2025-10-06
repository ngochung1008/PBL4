# client_controller.py

import json
import socket
from pynput.mouse import Controller as MouseController, Button
from pynput.keyboard import Controller as KeyboardController, Key

class ClientController:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.mouse = MouseController()
        self.keyboard = KeyboardController()

    def run(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((self.host, self.port))
            print("[CLIENT CONTROLLER] Connected to server")

            buffer = b""
            while True:
                data = sock.recv(4096)
                if not data:
                    break
                buffer += data

                # tách gói theo \n
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    event = json.loads(line.decode("utf-8"))
                    self.handle_event(event)

    def handle_event(self, event):
        if event["device"] == "mouse":
            self.handle_mouse(event)
        elif event["device"] == "keyboard":
            self.handle_keyboard(event)

    # ================= Mouse =================
    def handle_mouse(self, event):
        if event["type"] == "move":
            self.mouse.position = (event["x"], event["y"])
        elif event["type"] == "click":
            btn = self._map_button(event["button"])
            if btn:
                if event["pressed"]:
                    self.mouse.press(btn)
                else:
                    self.mouse.release(btn)
        elif event["type"] == "scroll":
            # scroll(dx, dy) → dx: ngang, dy: dọc
            self.mouse.scroll(event["dx"], event["dy"])

    def _map_button(self, btn_str):
        """Chuyển button string -> Button object"""
        if btn_str == "left":
            return Button.left
        elif btn_str == "right":
            return Button.right
        elif btn_str == "middle":
            return Button.middle
        return None

    # ================= Keyboard =================
    def handle_keyboard(self, event):
        if event["type"] == "type":
            self.keyboard.type(event["text"])
        elif event["type"] == "press":
            key = self._map_key(event["key"])
            if key:
                self.keyboard.press(key)
        elif event["type"] == "release":
            key = self._map_key(event["key"])
            if key:
                self.keyboard.release(key)

    def _map_key(self, key_str):
        """Chuyển tên phím từ JSON sang Key object hoặc ký tự thường"""
        try:
            return getattr(Key, key_str)  # ví dụ: "enter" -> Key.enter
        except AttributeError:
            return key_str  # phím thường (a, b, c, ...)