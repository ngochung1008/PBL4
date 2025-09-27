import socket
import json
import threading
from pynput import mouse, keyboard

class ManagerInput:
    def __init__(self, conn):
        self.conn = conn

    def send_event(self, event):
        try:
            msg = json.dumps(event).encode("utf-8")
            self.conn.sendall(msg)
        except Exception as e:
            print("[MANAGER INPUT] Send error:", e)

    # Mouse
    def on_move(self, x, y):
        self.send_event({"type": "move", "x": x, "y": y})

    def on_click(self, x, y, button, pressed):
        if pressed:
            if str(button) == "Button.right":
                self.send_event({"type": "rightclick"})
            else:
                self.send_event({"type": "click"})

    # Keyboard
    def on_press(self, key):
        try:
            if hasattr(key, 'char') and key.char is not None:
                self.send_event({"type": "type", "text": key.char})
            else:
                self.send_event({"type": "press", "key": key.name})
        except Exception:
            pass

    def run(self):
        # mouse listener
        t_mouse = threading.Thread(
            target=lambda: mouse.Listener(
                on_move=self.on_move, on_click=self.on_click
            ).run(),
            daemon=True
        )
        t_mouse.start()

        # keyboard listener
        with keyboard.Listener(on_press=self.on_press) as kl:
            kl.join()