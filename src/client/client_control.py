# client_control.py
import socket
import pyautogui

SERVER_HOST = "10.10.30.11"   # đổi sang IP server
SERVER_PORT = 9010

def execute_command(cmd: str):
    parts = cmd.strip().split()
    if not parts:
        return

    action = parts[0].upper()

    if action == "MOVE" and len(parts) == 3:
        x, y = int(parts[1]), int(parts[2])
        pyautogui.moveTo(x, y, duration=0.2)  # di chuyển chuột tới (x,y)
    elif action == "CLICK":
        pyautogui.click()
    elif action == "RIGHTCLICK":
        pyautogui.click(button="right")
    elif action == "TYPE" and len(parts) > 1:
        text = " ".join(parts[1:])
        pyautogui.typewrite(text)
    elif action == "PRESS" and len(parts) == 2:
        pyautogui.press(parts[1])  # ví dụ: PRESS enter
    else:
        print("Unknown command:", cmd)

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((SERVER_HOST, SERVER_PORT))
        print("Connected to server, waiting for commands...")
        while True:
            data = s.recv(1024)
            if not data:
                break
            cmd = data.decode("utf-8")
            print("Received:", cmd)
            execute_command(cmd)

if __name__ == "__main__":
    main()