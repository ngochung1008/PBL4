# manager_viewer.py
import socket, threading, io
from PIL import Image, ImageTk
import tkinter as tk
from common_network.x224_handshake import X224Handshake
from common_network.tpkt_layer import TPKTLayer
from common_network.pdu_parser import PDUParser

class ManagerViewer:
    def __init__(self, host, port, manager_id="manager1", on_click=None):
        self.host = host
        self.port = port
        self.manager_id = manager_id
        self.sock = None
        self.parser = PDUParser()
        self.root = tk.Tk()
        self.root.title(f"Manager Viewer - {manager_id}")
        self.canvas = tk.Canvas(self.root, bg="black")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.photo = None
        self.full_size = (0,0)  # last full frame size
        self.on_click = on_click   # callback(x,y,event)
        # bind mouse events for input capture
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<Motion>", self._on_motion)
        self.canvas.bind("<ButtonPress>", self._on_button)
        self.canvas.bind("<ButtonRelease>", self._on_button_release)
        self._mouse_pos = (0,0)

    def connect(self):
        self.sock = socket.create_connection((self.host, self.port), timeout=10)
        X224Handshake.client_send_connect(self.sock, self.manager_id)
        threading.Thread(target=self._recv_loop, daemon=True).start()

    def _recv_loop(self):
        try:
            while True:
                hdr = X224Handshake.recv_all(self.sock, 4)
                ver, rsv, length = TPKTLayer.unpack_header(hdr)
                body = X224Handshake.recv_all(self.sock, length - 4)
                pdu = self.parser.parse(body)
                if pdu["type"] == "full":
                    jpg = pdu["jpg"]
                    img = Image.open(io.BytesIO(jpg)).convert("RGB")
                    self.full_size = (pdu["width"], pdu["height"])
                    self._display_image(img)
                elif pdu["type"] == "rect":
                    jpg = pdu["jpg"]
                    img = Image.open(io.BytesIO(jpg)).convert("RGB")
                    # For simplicity we display rect alone.
                    # Advanced: composite into a backing full image.
                    self._display_image(img)
        except Exception as e:
            print("[VIEWER] recv loop stopped:", e)

    def _display_image(self, pil_img):
        # resize to fit canvas while maintaining aspect
        w, h = pil_img.size
        # perform UI update in main thread
        def _update():
            cw = self.canvas.winfo_width() or 800
            ch = self.canvas.winfo_height() or 600
            ratio = min(cw / w, ch / h, 1.0)
            nw = int(w * ratio)
            nh = int(h * ratio)
            img = pil_img.resize((nw, nh))
            self.photo = ImageTk.PhotoImage(img)
            self.canvas.delete("all")
            self.canvas.create_image((0,0), anchor="nw", image=self.photo)
        self.canvas.after(0, _update)

    def start_mainloop(self):
        self.root.mainloop()

    # mouse events -> call on_click handler with canvas coordinates
    def _on_click(self, event):
        x, y = event.x, event.y
        if self.on_click:
            self.on_click("click", x, y, event)

    def _on_motion(self, event):
        x, y = event.x, event.y
        self._mouse_pos = (x,y)
        if self.on_click:
            self.on_click("move", x, y, event)

    def _on_button(self, event):
        if self.on_click:
            self.on_click("down", event.x, event.y, event)

    def _on_button_release(self, event):
        if self.on_click:
            self.on_click("up", event.x, event.y, event)
