# manager_input.py

from pynput import mouse, keyboard
import json
import threading

""" Lớp quản lý input của Manager (chuột + bàn phím) 
Gửi sự kiện dưới dạng JSON qua socket kết nối với Server"""
class ManagerInput:
    def __init__(self, conn, viewer=None):
        self.conn = conn # socket kết nối tới Server
        """viewer: ManagerViewer: cho phép gọi hàm viewer.get_current_mapped_remote() để chuyển tọa độ chuột cục bộ thành tọa độ remote."""
        self.viewer = viewer # tham chiếu tới ManagerViewer (để lấy kích thước vùng hiển thị)"""
        """self._ignore: Cờ bảo vệ chống lại vòng lặp phản hồi (feedback loop). 
        Khi ManagerViewer tự động di chuyển con trỏ chuột cục bộ (sau khi nhận cập nhật con trỏ từ Client), 
        cờ này được đặt thành True để ngăn ManagerInput gửi sự kiện di chuyển tự động đó ngược lại cho Client."""
        self._ignore = False  
        self.is_controlling = False  # Theo dõi trạng thái chuột đang nằm trong vùng hiển thị remote

    def set_ignore(self, duration: float):
        """Tạm thời bỏ gửi local events trong duration giây."""
        try:
            self._ignore = True
            def _clear():
                self._ignore = False
            # ... (Sử dụng threading.Timer để đặt _ignore = True, sau duration thì đặt lại thành False)
            t = threading.Timer(duration, _clear)
            t.daemon = True
            t.start()
        except Exception as e:
            print("[MANAGER INPUT] set_ignore error:", e)

    def send_event(self, event: dict):
        """ Gửi sự kiện dạng JSON
        vd Dictionary này được chuyển thành chuỗi JSON 
        (ví dụ: {"device": "mouse", "type": "move", "x": 500, "y": 300}) """
        if self._ignore:
            return
        try:
            # ... (Chuyển đổi dictionary event thành chuỗi JSON và thêm '\n' để phân tách)
            msg = (json.dumps(event) + "\n").encode("utf-8")
            self.conn.sendall(msg)
        except Exception as e:
            print("[MANAGER INPUT] send_event error:", e)

    # ================== Mouse ==================
    def on_move(self, x, y):
        if self._ignore:
            return
        # Không dùng x,y từ pynput trực tiếp: lấy vị trí con trỏ trong viewer
        if not self.viewer:
            return
        
        # 1. Lấy tọa độ remote tương ứng với vị trí con trỏ CỤC BỘ của Manager
        mapped = self.viewer.get_current_mapped_remote()
        # Kiểm tra xem chuột có trong vùng hiển thị không
        if not mapped:
            if self.is_controlling:
                # Chuột vừa rời khỏi vùng điều khiển
                self.is_controlling = False
                print("[MANAGER INPUT] Mouse out of control area")
            return
        
        if not self.is_controlling:
            # Chuột vừa vào vùng điều khiển
            self.is_controlling = True
            print("[MANAGER INPUT] Mouse into control area")
        
        # 2. Gửi tọa độ (đã ánh xạ từ chuột Manager) đến Client
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
    # Được gọi ngay khi một phím bất kỳ trên bàn phím được nhấn xuống.
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

    # Được gọi ngay khi một phím bất kỳ trên bàn phím được nhả ra (thả lên).
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
        mouse_listener = mouse.Listener(
            on_move=self.on_move,
            on_click=self.on_click,
            on_scroll=self.on_scroll
        )
        mouse_listener.start()  # Chạy trong một luồng riêng

        with keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release
        ) as kl:
            """ Khởi động listener bàn phím và giữ luồng hiện tại 
            (thường là luồng được gọi ManagerInput.run() từ luồng chính) 
            hoạt động để tiếp tục lắng nghe các sự kiện bàn phím """
            kl.join()