# client_controller.py

import socket
import json
import threading
from datetime import datetime
from pynput.mouse import Controller as MouseController, Button
from pynput.keyboard import Controller as KeyboardController, Key
import time
import config 

CLIENT_SUPPRESS_DURATION_S = config.CLIENT_SUPPRESS_DURATION_S

class ClientController:
    def __init__(self, host, port, username="unknown", transfer_channel=None):
        self.host = host
        self.port = port
        self.mouse = MouseController() # Đối tượng điều khiển chuột cục bộ
        self.keyboard = KeyboardController() # Đối tượng điều khiển bàn phím cục bộ
        self._running = True
        self._suppress_until = 0.0 # Cờ chống vòng lặp phản hồi (cursor_update)
        # Vị trí client cuối cùng đã gửi
        self.last_client_x = -1
        self.last_client_y = -1
        self.username = username
        self.transfer_channel = transfer_channel

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
                if time.time() < getattr(self, "_suppress_until", 0):
                    time.sleep(0.01)
                    continue

                x, y = self.mouse.position

                # throttle + dedup
                if (abs(x - self.last_client_x) < config.THRESHOLD_DIST_C and
                        abs(y - self.last_client_y) < config.THRESHOLD_DIST_C):
                    time.sleep(0.05)  # giảm busy-loop
                    continue

                self.last_client_x = x
                self.last_client_y = y

                msg = json.dumps({
                    "device": "mouse",
                    "type": "cursor_update",
                    "x": int(x),
                    "y": int(y)
                }) + "\n"
                try:
                    sock.sendall(msg.encode("utf-8"))
                except Exception as e:
                    print("[CLIENT CONTROLLER] Cursor send error:", e)
                    break

                time.sleep(0.05)  # throttle: 20 updates/sec max
        except Exception as e:
            print("[CLIENT CONTROLLER] _send_cursor_updates error:", e)

    # ================== Mouse ==================
    def handle_mouse(self, event):
        if event["type"] == "move":
            if "x" in event and "y" in event:
                # khi lệnh move đến từ manager (remote), đặt con trỏ và tạm ngắt gửi cursor_update
                try:
                    self.mouse.position = (event["x"], event["y"])
                    # tạm dừng gửi cursor_update trong 400ms để tránh feedback loop
                    self._suppress_until = time.time() + CLIENT_SUPPRESS_DURATION_S # Bật cờ chống vòng lặp phản hồi
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
        if not self.transfer_channel: 
            return
        log_type = event["type"]
        try:
            """ Lệnh "type": Gõ các ký tự đơn giản.
                Lệnh "press"/"release": Sử dụng _map_key để chuyển tên phím """
            if log_type == "type":
                text = event.get("text", "")
                # Chỉ nhận ký tự in được
                if text and all(32 <= ord(c) < 127 for c in text):
                    self.keyboard.type(text)
                    self._send_log_to_server("type", text)

            elif log_type in ("press", "release"):
                key = self._map_key(event.get("key", ""))
                key_str = str(key).replace("Key.", "")
                if isinstance(key, Key) and key in [Key.ctrl, Key.alt, Key.cmd, Key.esc]:
                    print("[CLIENT CONTROLLER] Warning: Received special key:", key)
                if log_type == "press":
                    self.keyboard.press(key) 
                else:
                    self.keyboard.release(key)
                self._send_log_to_server(log_type, key_str)
        except Exception as e:
            print("[CLIENT CONTROLLER] handle_keyboard error:", e)

    # Gửi sự kiện log qua Transfer Channel
    def _send_log_to_server(self, event_type, key_info):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_data = {
            "timestamp": timestamp,
            "user": self.username,
            "event_type": event_type,
            "key": key_info
        }
        # Gửi gói "keylog" tới Server. Server sẽ relay cho Manager.
        self.transfer_channel.send_package("keylog", target_ip="all", data=log_data)

    def _map_key(self, key_str):
        """Chuyển tên phím từ JSON sang Key object hoặc ký tự thường"""
        try:
            return getattr(Key, key_str)  # ví dụ: "enter" -> Key.enter
        except AttributeError:
            return key_str  # phím thường (a, b, c, ...)