# manager_input.py
from pynput import mouse, keyboard

class ManagerInput:
    def __init__(self, sender, viewer):
        self.sender = sender
        self.viewer = viewer

    def on_move(self, x, y):
        rx, ry = self.viewer.map_to_remote(x, y)
        self.sender.send_input({"type": "mouse_move", "x": rx, "y": ry})

    def on_click(self, x, y, button, pressed):
        rx, ry = self.viewer.map_to_remote(x, y)
        btn = str(button).replace("Button.", "")
        self.sender.send_input({"type": "mouse_click", "x": rx, "y": ry, "button": btn, "pressed": pressed})

    def on_scroll(self, x, y, dx, dy):
        rx, ry = self.viewer.map_to_remote(x, y)
        self.sender.send_input({"type": "mouse_scroll", "x": rx, "y": ry, "dx": dx, "dy": dy})

    def on_press(self, key):
        self.sender.send_input({"type": "key_press", "key": str(key)})

    def on_release(self, key):
        self.sender.send_input({"type": "key_release", "key": str(key)})

    def run(self):
        mouse.Listener(
            on_move=self.on_move,
            on_click=self.on_click,
            on_scroll=self.on_scroll
        ).start()
        keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release
        ).start()
