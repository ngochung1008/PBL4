# manager_viewer.py
import io
import threading
import socket
import struct
import time
from PIL import Image, ImageTk
import tkinter as tk

from client_network.tpkt_layer import TPKTLayer
from client_network.pdu_builder import PDU_TYPE_FULL, PDU_TYPE_RECT


class ManagerViewer:
    def __init__(self, server_host, server_port, window_title="Remote Viewer"):
        self.server_host = server_host
        self.server_port = server_port
        self.window_title = window_title

        self.root = tk.Tk()
        self.root.title(self.window_title)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self.canvas = tk.Canvas(self.root, bg="black")
        self.canvas.pack(fill="both", expand=True)

        self.sock = None
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._recv_loop, daemon=True)

        # Biến chứa frame hiện tại
        self.image = None
        self.tk_img = None

        # Scale hiển thị (tự tính sau khi nhận full frame)
        self.display_scale = 1.0
        self.display_size = None

        # Thông tin kích thước thật
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

    # Nhận luồng dữ liệu ảnh từ server
    def _recv_loop(self):
        while not self.stop_event.is_set():
            try:
                print(f"[MANAGER] Connecting to {self.server_host}:{self.server_port} ...")
                self.sock = socket.create_connection((self.server_host, self.server_port), timeout=10)

                while not self.stop_event.is_set():
                    header = self._recv_exact(4)
                    if not header:
                        break
                    ver, rsv, total_len = struct.unpack(">BBH", header)
                    body = self._recv_exact(total_len - 4)
                    if not body:
                        break
                    self._handle_pdu(body)
            except Exception as e:
                print("[MANAGER] network error:", e)
                time.sleep(3)

    def _recv_exact(self, n):
        data = bytearray()
        while len(data) < n:
            chunk = self.sock.recv(n - len(data))
            if not chunk:
                return None
            data.extend(chunk)
        return bytes(data)

    # Xử lý frame nhận được
    def _handle_pdu(self, data):
        seq, ts_ms, pdu_type, flags = struct.unpack(">IQBB", data[:14])
        payload = data[14:]

        if pdu_type == PDU_TYPE_FULL:
            width, height, jpg_len = struct.unpack(">III", payload[:12])
            jpg_data = payload[12:12 + jpg_len]
            self._update_frame("full", jpg_data, width, height)

        elif pdu_type == PDU_TYPE_RECT:
            x, y, w, h, jpg_len = struct.unpack(">IIIII", payload[:20])
            full_w, full_h = struct.unpack(">II", payload[20:28])
            jpg_data = payload[28:28 + jpg_len]
            self._update_frame("rect", jpg_data, full_w, full_h, x, y)

    # Cập nhật canvas
    def _update_frame(self, frame_type, jpg_bytes, full_w, full_h, x=0, y=0):
        patch = Image.open(io.BytesIO(jpg_bytes))

        if frame_type == "full" or self.image is None:
            self.image = patch
            self.remote_width, self.remote_height = full_w, full_h

            # Tính tỉ lệ hiển thị để fit cửa sổ
            screen_w = self.root.winfo_screenwidth()
            screen_h = self.root.winfo_screenheight()
            scale = min(screen_w / full_w, screen_h / full_h)
            self.display_scale = scale
            self.display_size = (int(full_w * scale), int(full_h * scale))
            self.canvas.config(width=self.display_size[0], height=self.display_size[1])
        else:
            # Ghép vùng delta vào frame hiện có
            self.image.paste(patch, (x, y))

        # Resize để hiển thị
        display_img = self.image.resize(self.display_size)
        self.tk_img = ImageTk.PhotoImage(display_img)
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_img)
        self.canvas.image = self.tk_img

    # Lấy tỷ lệ hiển thị để tính ngược toạ độ
    def get_scale_ratio(self):
        """Tỷ lệ từ màn hình hiển thị → màn hình gốc client"""
        if not self.remote_width or not self.remote_height:
            return 1.0
        return self.remote_width / self.display_size[0]
