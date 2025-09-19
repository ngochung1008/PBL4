# client.py
import socket
import pyautogui

SERVER_HOST = "127.0.0.1"   # IP server
SERVER_PORT = 9011          # cổng dành cho Client

def execute_command(cmd: str):
    parts = cmd.strip().split()
    if not parts: return
    action = parts[0].upper()
    if action == "MOVE" and len(parts) == 3:
        x, y = int(parts[1]), int(parts[2])
        pyautogui.moveTo(x, y, duration=0.2)
    elif action == "CLICK":
        pyautogui.click()
    elif action == "TYPE":
        text = " ".join(parts[1:])
        pyautogui.typewrite(text)
    else:
        print("Unknown command:", cmd)

def main():
    with socket.create_connection((SERVER_HOST, SERVER_PORT)) as s:
        print("Connected to server, waiting for commands...")
        while True:
            data = s.recv(1024)
            if not data:
                break
            cmd = data.decode("utf-8")
            print("Received:", cmd)
            execute_command(cmd)
            # phản hồi về server (tùy chọn)
            s.sendall(f"Executed: {cmd}".encode("utf-8"))

if __name__ == "__main__":
    main()