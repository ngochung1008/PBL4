# manager_input.py

import json
import threading
from pynput import mouse, keyboard

class ManagerInput:
    """
    Lớp quản lý input của Manager (chuột + bàn phím)
    Gửi sự kiện dưới dạng JSON qua socket kết nối với Server
    """

    def __init__(self, conn, viewer=None):
        self.conn = conn
        self.viewer = viewer

    def send_event(self, event: dict):
        """Gửi sự kiện dạng JSON"""
        try:
            msg = (json.dumps(event) + "\n").encode("utf-8")
            # thêm \n để phân tách gói khi gửi liên tục
            self.conn.sendall(msg)
        except Exception as e:
            print("[MANAGER INPUT] Send error:", e)

    # ================== Mouse ==================
    def on_move(self, x, y):
        try:
                scale_x = getattr(self.viewer, "scale_x", 1.0) if self.viewer else 1.0
                scale_y = getattr(self.viewer, "scale_y", 1.0) if self.viewer else 1.0
                scaled_x = int(x * scale_x)
                scaled_y = int(y * scale_y)
        except Exception:
            scaled_x = int(x)
            scaled_y = int(y)

        self.send_event({
            "device": "mouse",
            "type": "move",
            "x": scaled_x,
            "y": scaled_y
        })

    def on_click(self, x, y, button, pressed):
        btn = str(button).replace("Button.", "")
        try:
                scale_x = getattr(self.viewer, "scale_x", 1.0) if self.viewer else 1.0
                scale_y = getattr(self.viewer, "scale_y", 1.0) if self.viewer else 1.0
                sx = int(x * scale_x)
                sy = int(y * scale_y)
        except Exception:
            sx, sy = int(x), int(y)

        self.send_event({
            "device": "mouse",
            "type": "click",
            "button": btn,
            "pressed": pressed,
            "x": sx,
            "y": sy
        })

    def on_scroll(self, x, y, dx, dy):
        self.send_event({
            "device": "mouse",
            "type": "scroll",
            "x": x,
            "y": y,
            "dx": dx,
            "dy": dy
        })

    # ================== Keyboard ==================
    def on_press(self, key):
        try:
            if hasattr(key, "char") and key.char is not None:
                # Phím ký tự
                self.send_event({
                    "device": "keyboard",
                    "type": "type",
                    "text": key.char
                })
            else:
                # Phím đặc biệt (enter, shift, ctrl, alt, arrow, function keys...)
                self.send_event({
                    "device": "keyboard",
                    "type": "press",
                    "key": str(key).replace("Key.", "")
                })
        except Exception as e:
            print("[KEYBOARD] Press error:", e)

    def on_release(self, key):
        try:
            if hasattr(key, "char") and key.char is not None:
                self.send_event({
                    "device": "keyboard",
                    "type": "release",
                    "text": key.char
                })
            else:
                self.send_event({
                    "device": "keyboard",
                    "type": "release",
                    "key": str(key).replace("Key.", "")
                })
        except Exception as e:
            print("[KEYBOARD] Release error:", e)

    # ================== Run Listeners ==================
    def run(self):
        """Khởi động listener cho chuột + bàn phím"""
        # Chuột chạy thread riêng
        t_mouse = threading.Thread(
            target=lambda: mouse.Listener(
                on_move=self.on_move,
                on_click=self.on_click,
                on_scroll=self.on_scroll
            ).run(),
            daemon=True
        )
        t_mouse.start()

        # Bàn phím chạy thread chính
        with keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release
        ) as kl:
            kl.join()