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
        self._ignore = False  # khi True: không gửi những move đến server (dùng để tránh loop)
        self.is_controlling = False  # Thêm trạng thái điều khiển

    def set_ignore(self, duration: float):
        """Tạm thời bỏ gửi local events trong duration giây."""
        try:
            self._ignore = True
            def _clear():
                self._ignore = False
            t = threading.Timer(duration, _clear)
            t.daemon = True
            t.start()
        except Exception as e:
            print("[MANAGER INPUT] set_ignore error:", e)

    def send_event(self, event: dict):
        """Gửi sự kiện dạng JSON"""
        if self._ignore:
            return
        try:
            msg = (json.dumps(event) + "\n").encode("utf-8")
            # thêm \n để phân tách gói khi gửi liên tục
            self.conn.sendall(msg)
        except Exception as e:
            print("[MANAGER INPUT] Send error:", e)

    # ================== Mouse ==================
    def on_move(self, x, y):
        if self._ignore:
            return
        # Không dùng x,y từ pynput trực tiếp: lấy vị trí con trỏ trong viewer
        if not self.viewer:
            return
        
        # Kiểm tra xem chuột có trong vùng hiển thị không
        mapped = self.viewer.get_current_mapped_remote()
        if not mapped:
            if self.is_controlling:
                # Chuột vừa rời khỏi vùng điều khiển
                self.is_controlling = False
                print("[MANAGER INPUT] Mouse left control area")
            return
        
        if not self.is_controlling:
            # Chuột vừa vào vùng điều khiển
            self.is_controlling = True
            print("[MANAGER INPUT] Mouse entered control area")
        
        # Gửi tọa độ chỉ khi đang trong vùng điều khiển
        scaled_x, scaled_y = mapped
        self.send_event({
            "device": "mouse", 
            "type": "move",
            "x": scaled_x,
            "y": scaled_y
        })

    def on_click(self, x, y, button, pressed):
        if self._ignore:
            return
        if not self.viewer:
            return
        mapped = self.viewer.get_current_mapped_remote()
        if not mapped:
            return
        sx, sy = mapped
        btn = str(button).replace("Button.", "")
        self.send_event({
            "device": "mouse",
            "type": "click",
            "button": btn,
            "pressed": pressed,
            "x": sx,
            "y": sy
        })

    def on_scroll(self, x, y, dx, dy):
        if self._ignore:
            return
        # gửi scroll chỉ khi trong vùng
        if not self.viewer:
            return
        mapped = self.viewer.get_current_mapped_remote()
        if not mapped:
            return
        self.send_event({
            "device": "mouse",
            "type": "scroll",
            "x": mapped[0],
            "y": mapped[1],
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
        # Thay đoạn này:
        mouse_listener = mouse.Listener(
            on_move=self.on_move,
            on_click=self.on_click,
            on_scroll=self.on_scroll
        )
        mouse_listener.start()  # dùng start() thay vì .run()

        with keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release
        ) as kl:
            kl.join()