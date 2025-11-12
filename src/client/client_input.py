"""
client_input.py

Nhận PDU INPUT_EVENT từ server và thực thi tại máy client.
"""

import pyautogui
import threading
import json
from client.common_network.pdu_parser import PDUParser  # dùng parser để tách payload
from client.common_network.pdu_builder import PDUBuilder

class ClientInputHandler:
    def __init__(self, transport):
        self.transport = transport
        self.stop = False
        self.thread = None

    def start(self):
        self.stop = False
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def stop_loop(self):
        self.stop = True

    def _loop(self):
        print("[CLIENT_INPUT] Listening for INPUT_EVENT...")
        while not self.stop:
            pdu = self.transport.recv_pdu(timeout=0.2)
            if not pdu:
                continue
            if pdu["type"] != "INPUT_EVENT":
                continue

            try:
                data = json.loads(pdu["payload"].decode("utf-8"))
                self._execute_event(data)
            except Exception as e:
                print("[CLIENT_INPUT] Error decoding event:", e)

    def _execute_event(self, ev):
        t = ev.get("type")
        if t == "mouse_move":
            pyautogui.moveTo(ev["x"], ev["y"])
        elif t == "mouse_click":
            pyautogui.click(button=ev.get("button", "left"))
        elif t == "mouse_scroll":
            pyautogui.scroll(ev.get("delta", 0))
        elif t == "key_press":
            pyautogui.keyDown(ev["key"])
        elif t == "key_release":
            pyautogui.keyUp(ev["key"])
        else:
            print("[CLIENT_INPUT] Unknown event:", ev)
