"""
manager_viewer.py

Hiển thị màn hình từ client (manager nhận frame JPG từ server và vẽ bằng Tkinter)
"""

import io
import threading
import time
from PIL import Image, ImageTk
import tkinter as tk

class ManagerViewer:
    def __init__(self, transport, window_title="Remote Screen"):
        self.transport = transport
        self.root = tk.Tk()
        self.root.title(window_title)
        self.label = tk.Label(self.root)
        self.label.pack()
        self.stop = False
        self.current_frame = None

    def start(self):
        threading.Thread(target=self._recv_loop, daemon=True).start()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()

    def _recv_loop(self):
        print("[MANAGER_VIEWER] Listening for screen frames...")
        while not self.stop:
            msg = self.transport.recv_message(timeout=0.2)
            if not msg:
                continue
            try:
                frame_bytes = msg if isinstance(msg, bytes) else msg.encode()
                img = Image.open(io.BytesIO(frame_bytes))
                self.current_frame = ImageTk.PhotoImage(img)
                self.label.config(image=self.current_frame)
            except Exception as e:
                print("[MANAGER_VIEWER] Frame decode failed:", e)
                time.sleep(0.1)

    def _on_close(self):
        self.stop = True
        self.root.destroy()
