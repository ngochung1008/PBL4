import socket
import struct
import time
import io
import pyautogui
from mss import mss
from PIL import Image
import threading

SERVER_HOST = "10.10.30.179"   # IP server
CONTROL_PORT = 9011         # phải khớp với server (CONTROL_PORT+1)
SCREEN_PORT = 5000
FPS = 1

# ========================
# XỬ LÝ LỆNH TỪ SERVER
# ========================
def execute_command(cmd: str):
    parts = cmd.strip().split()
    if not parts:
        return
    action = parts[0].upper()
    try:
        if action == "MOVE" and len(parts) == 3:
            x, y = int(parts[1]), int(parts[2])
            pyautogui.moveTo(x, y, duration=0.2)
        elif action == "CLICK":
            pyautogui.click()
        elif action == "RIGHTCLICK":
            pyautogui.click(button="right")
        elif action == "TYPE" and len(parts) > 1:
            text = " ".join(parts[1:])
            pyautogui.typewrite(text)
        elif action == "PRESS" and len(parts) == 2:
            pyautogui.press(parts[1])
        else:
            print("Unknown command:", cmd)
    except Exception as e:
        print("Error executing:", e)

def client_control():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((SERVER_HOST, CONTROL_PORT))
        print("[CLIENT B] Connected to control server")
        while True:
            data = s.recv(1024)
            if not data:
                break
            cmd = data.decode("utf-8")
            print("[CLIENT B] Received:", cmd)
            execute_command(cmd)

# ========================
# GỬI MÀN HÌNH
# ========================
def capture_jpeg_bytes(monitor_index=0, quality=60):
    with mss() as sct:
        monitor = sct.monitors[monitor_index]
        sct_img = sct.grab(monitor)
        img = Image.frombytes("RGB", sct_img.size, sct_img.rgb)
        bio = io.BytesIO()
        img.save(bio, format="JPEG", quality=quality)
        return bio.getvalue()

def client_screen(fps=1):
    interval = 1.0 / fps
    while True:
        try:
            with socket.create_connection((SERVER_HOST, SCREEN_PORT)) as s:
                print("[CLIENT B] Connected to screen server")
                while True:
                    start = time.time()
                    jpg = capture_jpeg_bytes()
                    length = struct.pack(">I", len(jpg))
                    s.sendall(length + jpg)
                    elapsed = time.time() - start
                    time.sleep(max(0, interval - elapsed))
        except Exception as e:
            print("Screen connection error:", e)
            time.sleep(5)

# ========================
# MAIN
# ========================
if __name__ == "__main__":
    threading.Thread(target=client_control, daemon=True).start()
    client_screen(FPS)