"""
manager_input.py

Ghi nhận thao tác chuột / bàn phím tại manager → gửi về server (qua transport)
"""

from pynput import mouse, keyboard
import json
import threading

class ManagerInputSender:
    def __init__(self, transport):
        self.transport = transport
        self._mouse_listener = None
        self._keyboard_listener = None
        self.stop = False

    def start(self):
        self.stop = False
        threading.Thread(target=self._start_mouse, daemon=True).start()
        threading.Thread(target=self._start_keyboard, daemon=True).start()

    def stop_all(self):
        self.stop = True
        if self._mouse_listener:
            self._mouse_listener.stop()
        if self._keyboard_listener:
            self._keyboard_listener.stop()

    def _start_mouse(self):
        def on_move(x, y):
            self._send({"type": "mouse_move", "x": x, "y": y})

        def on_click(x, y, button, pressed):
            if pressed:
                self._send({"type": "mouse_click", "x": x, "y": y, "button": str(button)})

        def on_scroll(x, y, dx, dy):
            self._send({"type": "mouse_scroll", "delta": dy})

        self._mouse_listener = mouse.Listener(on_move=on_move, on_click=on_click, on_scroll=on_scroll)
        self._mouse_listener.start()
        self._mouse_listener.join()

    def _start_keyboard(self):
        def on_press(key):
            try:
                k = key.char or str(key)
            except:
                k = str(key)
            self._send({"type": "key_press", "key": k})

        def on_release(key):
            try:
                k = key.char or str(key)
            except:
                k = str(key)
            self._send({"type": "key_release", "key": k})

        self._keyboard_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        self._keyboard_listener.start()
        self._keyboard_listener.join()

    def _send(self, msg_dict):
        try:
            self.transport.send_message(json.dumps(msg_dict))
        except Exception as e:
            print("[MANAGER_INPUT] Send failed:", e)
