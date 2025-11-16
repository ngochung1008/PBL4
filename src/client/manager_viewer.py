# manager_viewer.py
import io
import socket
import struct
import threading
import time
from PIL import Image, ImageTk
import tkinter as tk

PDU_TYPE_FULL = 1
PDU_TYPE_RECT = 2

TPKT_HEADER_FMT = ">BBH"
SHARE_CTRL_HDR_FMT = ">IQBB"  # seq, timestamp, pdu_type, flags

def recv_all(sock, n):
    data = b""
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            raise ConnectionError("Socket closed")
        data += chunk
    return data

class ManagerViewer:
    def __init__(self, server_host, server_port, window_title="Remote Viewer"):
        self.server_host = server_host
        self.server_port = server_port
        self.window_title = window_title

        self.root = tk.Tk()
        self.root.title(window_title)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.canvas = tk.Canvas(self.root, bg="black")
        self.canvas.pack(fill="both", expand=True)

        self.sock = None
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._recv_loop, daemon=True)

        self.image = None
        self.tk_img = None

        self.display_size = None
        self.remote_width = None
        self.remote_height = None

    def start(self):
        self.thread.start()
        self.root.mainloop()

    def _on_close(self):
        self.stop_event.set()
        if self.sock:
            self.sock.close()
        self.root.destroy()

    def _recv_loop(self):
        while not self.stop_event.is_set():
            try:
                print(f"[VIEWER] Connecting to {self.server_host}:{self.server_port}")
                self.sock = socket.create_connection((self.server_host, self.server_port), timeout=10)
                self.sock.sendall(b"MANAGER\n")  # handshake

                while not self.stop_event.is_set():
                    header = recv_all(self.sock, 4)
                    ver, rsv, total_len = struct.unpack(TPKT_HEADER_FMT, header)
                    body = recv_all(self.sock, total_len - 4)
                    self._handle_pdu(body)
            except Exception as e:
                print("[VIEWER] Network error:", e)
                time.sleep(3)

    def _handle_pdu(self, data):
        if len(data) < struct.calcsize(SHARE_CTRL_HDR_FMT):
            return
        seq, ts_ms, pdu_type, flags = struct.unpack(SHARE_CTRL_HDR_FMT, data[:14])
        payload = data[14:]

        if pdu_type == PDU_TYPE_FULL:
            if len(payload) < 12:
                return
            width, height, jpg_len = struct.unpack(">III", payload[:12])
            jpg_data = payload[12:12 + jpg_len]
            self._update_frame("full", jpg_data, width, height)
        elif pdu_type == PDU_TYPE_RECT:
            if len(payload) < 28:
                return
            x, y, w, h, jpg_len = struct.unpack(">IIIII", payload[:20])
            full_w, full_h = struct.unpack(">II", payload[20:28])
            jpg_data = payload[28:28 + jpg_len]
            self._update_frame("rect", jpg_data, full_w, full_h, x, y)

    def _update_frame(self, frame_type, jpg_bytes, full_w, full_h, x=0, y=0):
        patch = Image.open(io.BytesIO(jpg_bytes))
        if frame_type == "full" or self.image is None:
            self.image = patch
            self.remote_width, self.remote_height = full_w, full_h
            screen_w = self.root.winfo_screenwidth()
            screen_h = self.root.winfo_screenheight()
            scale = min(screen_w / full_w, screen_h / full_h)
            self.display_size = (int(full_w * scale), int(full_h * scale))
            self.canvas.config(width=self.display_size[0], height=self.display_size[1])
        else:
            if self.image.size != (full_w, full_h):
                self.image = Image.new("RGB", (full_w, full_h))
            self.image.paste(patch, (x, y))

        display_img = self.image.resize(self.display_size)
        self.tk_img = ImageTk.PhotoImage(display_img)
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_img)
        self.canvas.image = self.tk_img

    def map_to_remote(self, mx, my):
        """Chuyển từ màn hình manager -> tọa độ client"""
        if not self.remote_width or not self.remote_height or not self.display_size:
            return mx, my
        scale_x = self.remote_width / self.display_size[0]
        scale_y = self.remote_height / self.display_size[1]
        return int(mx * scale_x), int(my * scale_y)
