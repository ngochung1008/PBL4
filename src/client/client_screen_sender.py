# client_screen_sender.py

import socket
import time
import threading
import io
from queue import Queue
from client_network.tpkt_layer import TPKTLayer
from client_network.x224_handshake import X224Handshake
from client_network.mcs_layer import MCSLite
from client_network.security_layer import SecurityLayer
from client_network.pdu_builder import PDUBuilder

class ClientScreenSender:
    """Gửi frame chụp màn hình từ Client lên Server qua giao thức mô phỏng RDP"""
    def __init__(self, host, port, client_id, use_encryption=False, rect_threshold_area=20000):
        self.host = host
        self.port = port
        self.client_id = client_id
        self.security = SecurityLayer(use_encryption)
        self.x224 = X224Handshake(client_id)
        self.mcs = MCSLite()
        self.seq = 0
        self.queue = Queue(maxsize=2)
        self.stop_event = threading.Event()
        self.rect_threshold_area = rect_threshold_area

    def enqueue_frame(self, width, height, jpg_bytes, bbox, pil_image):
        """Thêm frame hoặc vùng delta vào hàng đợi để gửi"""
        try:
            if bbox:
                left, upper, right, lower = bbox
                area = (right - left) * (lower - upper)
                if area <= self.rect_threshold_area:
                    rect_img = pil_image.crop((left, upper, right, lower))
                    bio = io.BytesIO()
                    rect_img.save(bio, format="JPEG", quality=75)
                    rect_jpg = bio.getvalue()
                    payload = {"type": "rect", "width": width, "height": height,
                               "x": left, "y": upper, "w": right-left, "h": lower-upper,
                               "jpg": rect_jpg}
                else:
                    payload = {"type": "full", "width": width, "height": height, "jpg": jpg_bytes}
            else:
                payload = {"type": "full", "width": width, "height": height, "jpg": jpg_bytes}

            if self.queue.full():
                self.queue.get_nowait()
            self.queue.put(payload)
        except Exception as e:
            print("[SENDER] enqueue_frame error:", e)

    def _send_via_socket(self, sock, data_bytes):
        encrypted = self.security.encrypt(data_bytes)
        tpkt = TPKTLayer.pack(encrypted)
        sock.sendall(tpkt)

    def send_loop(self):
        """Kết nối tới server và gửi frame liên tục"""
        while not self.stop_event.is_set():
            sock = None
            try:
                print(f"[SENDER] Connecting to {self.host}:{self.port} ...")
                sock = socket.create_connection((self.host, self.port), timeout=10)

                if not self.x224.do_handshake(sock):
                    print("[SENDER] Handshake failed.")
                    sock.close()
                    time.sleep(3)
                    continue

                chan_msg = f"CHANNEL:{self.mcs.get_channel_id()}".encode()
                ctrl_pdu = PDUBuilder.build_control_pdu(self.seq, chan_msg)
                self._send_via_socket(sock, ctrl_pdu)
                self.seq += 1

                while not self.stop_event.is_set():
                    try:
                        payload = self.queue.get(timeout=1)
                        if payload["type"] == "full":
                            pdu = PDUBuilder.build_full_frame_pdu(self.seq, payload["jpg"], payload["width"], payload["height"])
                        else:
                            pdu = PDUBuilder.build_rect_frame_pdu(self.seq,
                                payload["jpg"], payload["x"], payload["y"], payload["w"], payload["h"],
                                payload["width"], payload["height"])
                        self._send_via_socket(sock, pdu)
                        self.seq += 1
                        print(f"[SENDER] seq={self.seq}, type={payload['type']}, bytes={len(pdu)}")
                    except Exception:
                        pass
            except Exception as e:
                print("[SENDER] network error:", e)
                if sock:
                    sock.close()
                time.sleep(5)

    def stop_sender(self):
        self.stop_event.set()
