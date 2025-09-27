import socket
import json
import pyautogui

class ClientInput:
    def __init__(self, server_host, input_port):
        self.server_host = server_host
        self.input_port = input_port

    def execute_input(self, event: dict):
        try:
            etype = event.get("type")
            if etype == "move":
                pyautogui.moveTo(event["x"], event["y"], duration=0.05)
            elif etype == "click":
                pyautogui.click()
            elif etype == "rightclick":
                pyautogui.click(button="right")
            elif etype == "type":
                pyautogui.typewrite(event["text"])
            elif etype == "press":
                pyautogui.press(event["key"])
            else:
                print("[CLIENT INPUT] Unknown event:", event)
        except Exception as e:
            print("[CLIENT INPUT] Error:", e)

    def run(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.server_host, self.input_port))
            print("[CLIENT INPUT] Connected to input server")
            while True:
                data = s.recv(4096)
                if not data:
                    break
                try:
                    event = json.loads(data.decode("utf-8"))
                    self.execute_input(event)
                except json.JSONDecodeError:
                    print("[CLIENT INPUT] Invalid JSON:", data)
