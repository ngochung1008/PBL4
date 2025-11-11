# client/client_input_handler.py
"file dùng"

import struct
import pyautogui

class ClientInputHandler:
    """Nhận input từ Manager (qua server) và thực thi"""
    def __init__(self, network):
        self.network = network
        self.running = True

    def handle_loop(self):
        """Vòng lặp lắng nghe channel input"""
        while self.running:
            raw = self.network.recv_raw()
            if not raw:
                break
            # Mở gói MCS để xem channel
            channel_name, payload = self.network.mcs.unpack(raw)
            if channel_name != "input":
                continue
            # Giải mã PDU input (giả định: 'type|x|y|btn')
            parts = payload.decode("utf-8").split("|")
            if parts[0] == "mouse":
                _, x, y, btn = parts
                pyautogui.moveTo(int(x), int(y))
                if btn == "left":
                    pyautogui.click()
            elif parts[0] == "keyboard":
                _, key, action = parts
                if action == "down":
                    pyautogui.keyDown(key)
                else:
                    pyautogui.keyUp(key)
