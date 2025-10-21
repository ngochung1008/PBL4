# client_controller.py

import socket
import json
import threading
from pynput.mouse import Controller as MouseController, Button
from pynput.keyboard import Controller as KeyboardController, Key
import time

class ClientController:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.mouse = MouseController() # Đối tượng điều khiển chuột cục bộ
        self.keyboard = KeyboardController() # Đối tượng điều khiển bàn phím cục bộ
        self._running = True
        self._suppress_until = 0.0 # Cờ chống vòng lặp phản hồi (cursor_update)

    def run(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((self.host, self.port))
            print("[CLIENT CONTROLLER] Connected to server for control")

            """ _send_cursor_updates Thread: Khởi động một luồng riêng biệt (thread) để xử lý 
            việc gửi vị trí con trỏ chuột của Client lên Server một cách định kỳ. 
            daemon=True đảm bảo luồng này sẽ tự động dừng khi chương trình chính dừng. """
            threading.Thread(target=self._send_cursor_updates, args=(sock,), daemon=True).start()

            # Nhận và xử lý sự kiện từ server
            buffer = b""
            while True:
                data = sock.recv(4096)
                if not data:
                    break
                buffer += data

                # Giới hạn buffer để tránh kẹt
                if len(buffer) > 65536:
                    buffer = b""

                # Phân tách gói vì manager gửi các lệnh JSON cách nhau bằng '\n'
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    try:
                        event = json.loads(line.decode("utf-8"))
                        threading.Thread(target=self.handle_event, args=(event,), daemon=True).start()
                    except Exception as e:
                        print("[CLIENT CONTROLLER] Parse error:", e)

    # Xử lý sự kiện nhận được từ server (lệnh điều khiển từ manager)
    def handle_event(self, event):
        if event["device"] == "mouse":
            self.handle_mouse(event)
        elif event["device"] == "keyboard":
            self.handle_keyboard(event)

    # Gửi định kỳ vị trí con chuột của client lên server để manager có thể hiển thị.
    def _send_cursor_updates(self, sock):
        try:
            while True:
                # 1. Kiểm tra cờ chống vòng lặp
                if time.time() < getattr(self, "_suppress_until", 0):
                    time.sleep(0.05)
                    continue

                # 2. Lấy vị trí con trỏ chuột hiện tại (cục bộ)
                x, y = self.mouse.position

                # 3. Đóng gói JSON
                msg = json.dumps({
                    "device": "mouse",
                    "type": "cursor_update",
                    "x": int(x),
                    "y": int(y)
                }) + "\n"

                # 4. Gửi và chờ qua socket
                try:
                    sock.sendall(msg.encode("utf-8")) # Gửi vị trí này dưới lệnh "cursor_update" đến Manager
                except Exception:
                    # socket có thể đã đóng
                    break
                time.sleep(0.2) # Chờ 200ms trước khi cập nhật tiếp theo
        except Exception:
            pass

    # ================== Mouse ==================
    def handle_mouse(self, event):
        if event["type"] == "move":
            if "x" in event and "y" in event:
                # khi lệnh move đến từ manager (remote), đặt con trỏ và tạm ngắt gửi cursor_update
                try:
                    self.mouse.position = (event["x"], event["y"])
                    # tạm dừng gửi cursor_update trong 250ms để tránh feedback loop
                    self._suppress_until = time.time() + 0.25 # Bật cờ chống vòng lặp phản hồi
                except Exception as e:
                    print("[CLIENT] Set (position) handle_mouse error:", e)
        elif event["type"] == "click":
            btn = self._map_button(event["button"])
            if btn:
                if event["pressed"]:
                    self.mouse.press(btn) # nhấn nút
                else:
                    self.mouse.release(btn) # thả nút
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
            """ Lệnh "type": Gõ các ký tự đơn giản.
                Lệnh "press"/"release": Sử dụng _map_key để chuyển tên phím """
            if event["type"] == "type": 
                text = event.get("text", "")
                # Chỉ nhận ký tự in được
                if text and all(32 <= ord(c) < 127 for c in text):
                    self.keyboard.type(text)

            elif event["type"] in ("press", "release"):
                key = self._map_key(event.get("key", ""))
                if isinstance(key, Key) and key in [Key.ctrl, Key.alt, Key.cmd, Key.esc]:
                    print("[CLIENT CONTROLLER] Warning: Received special key:", key)
                if event["type"] == "press":
                    self.keyboard.press(key) # nhấn phím đặc biệt 
                else:
                    self.keyboard.release(key) # thả phím đặc biệt
        except Exception as e:
            print("[CLIENT CONTROLLER] handle_keyboard error:", e)

    def _map_key(self, key_str):
        """Chuyển tên phím từ JSON sang Key object hoặc ký tự thường"""
        try:
            return getattr(Key, key_str)  # ví dụ: "enter" -> Key.enter
        except AttributeError:
            return key_str  # phím thường (a, b, c, ...)