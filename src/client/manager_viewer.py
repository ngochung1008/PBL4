# File: manager_viewer.py
"""
A simple Tkinter-based viewer that connects to server via ManagerClient, receives PDUs and displays the latest frame.
"""
import threading
from client.manager_client import ManagerClient
from PIL import Image, ImageTk
import io
import tkinter as tk
import time 

class ManagerViewer:
    def __init__(self, server_host, server_port, manager_id='manager1'):
        self.client = ManagerClient(server_host, server_port, manager_id)
        self.root = tk.Tk()
        self.root.title(f"Manager Viewer - {manager_id}")
        self.label = tk.Label(self.root)
        self.label.pack()
        self.last_image = None
        self.client.on_frame = self.on_pdu

    def on_pdu(self, pdu):
        try:
            if pdu['type'] == 'full':
                jpg = pdu['jpg']
                img = Image.open(io.BytesIO(jpg)).convert('RGB')
            elif pdu['type'] == 'rect':
                # For simplicity, show rect alone. In practice you'd composite into full canvas.
                jpg = pdu['jpg']
                img = Image.open(io.BytesIO(jpg)).convert('RGB')
            else:
                return
            # resize to fit window
            img.thumbnail((1280, 720))
            self.last_image = ImageTk.PhotoImage(img)
            # update GUI in main thread
            self.label.after(0, lambda: self.label.config(image=self.last_image))
        except Exception as e:
            print("[VIEWER] decode/display error:", e)

    def start(self):
        self.client.connect()
        threading.Thread(target=self.root.mainloop, daemon=True).start()


if __name__ == '__main__':
    viewer = ManagerViewer('10.10.30.88', 33890, 'manager:viewer1')
    viewer.start()
    # keep main thread alive
    while True:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            viewer.client.close()
            break