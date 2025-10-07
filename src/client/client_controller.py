# client_controller.py

import socket
import json
import threading
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

                # Giới hạn buffer để tránh kẹt
                if len(buffer) > 65536:
                    buffer = b""

                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    try:
                        event = json.loads(line.decode("utf-8"))
                        threading.Thread(target=self.handle_event, args=(event,), daemon=True).start()
                    except Exception as e:
                        print("[CLIENT CONTROLLER] Parse error:", e)


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
        try:
            if event["type"] == "type":
                text = event.get("text", "")
                # Chỉ nhận ký tự in được
                if text and all(32 <= ord(c) < 127 for c in text):
                    self.keyboard.type(text)

            elif event["type"] in ("press", "release"):
                key = self._map_key(event.get("key", ""))
                if key in [Key.ctrl, Key.alt, Key.cmd, Key.esc]:
                    print("[CLIENT CONTROLLER] Ignored special key:", key)
                    return
                if event["type"] == "press":
                    self.keyboard.press(key)
                else:
                    self.keyboard.release(key)
        except Exception as e:
            print("[CLIENT CONTROLLER] Keyboard error:", e)

    def _map_key(self, key_str):
        """Chuyển tên phím từ JSON sang Key object hoặc ký tự thường"""
        try:
            return getattr(Key, key_str)  # ví dụ: "enter" -> Key.enter
        except AttributeError:
            return key_str  # phím thường (a, b, c, ...)