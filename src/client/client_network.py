# client_network.py
# -*- coding: utf-8 -*-
"""
ClientNetwork chứa:
- TPKT packing
- X224-style simple handshake (mô phỏng)
- MCS-lite: gán một virtual channel id
- SecurityLayer (AES-CBC) nếu Crypto.Cipher có sẵn; nếu không có thì skip (modular)
- PDU builder: ShareControlHeader + BitmapUpdate (full or rect)
- send_loop kết hợp với queue/luồng an toàn
"""

import socket
import struct
import time
import threading
from queue import Queue
import io

# Try AES (PyCryptodome) – optional
try:
    from Crypto.Cipher import AES
    from Crypto.Random import get_random_bytes
    AES_AVAILABLE = True
except Exception:
    AES_AVAILABLE = False

TPKT_HEADER_FMT = ">BBH"
TPKT_OVERHEAD = 4
MAX_TPKT_LENGTH = 65535

# PDU types (mô phỏng)
PDU_TYPE_FULL = 1
PDU_TYPE_RECT = 2
PDU_TYPE_CONTROL = 3

# Share control header format:
# >I Q B B  -> seq (4), timestamp_ms (8), pdu_type (1), flags (1)
SHARE_CTRL_HDR_FMT = ">IQBB"
SHARE_CTRL_HDR_SIZE = struct.calcsize(SHARE_CTRL_HDR_FMT)  # 4 + 8 + 1 + 1 = 14 bytes

# Frame header for full frame: width(4), height(4), jpeg_len(4)
FRAME_FULL_HDR_FMT = ">III"
FRAME_FULL_HDR_SIZE = struct.calcsize(FRAME_FULL_HDR_FMT)

# Frame header for rect: x,y,w,h, jpeg_len
FRAME_RECT_HDR_FMT = ">IIII I"
FRAME_RECT_HDR_SIZE = struct.calcsize(FRAME_RECT_HDR_FMT)  # 5 ints

class SecurityLayer:
    """
    Nếu AES_AVAILABLE True, hỗ trợ encrypt/decrypt bằng AES-CBC.
    Khóa được tạo ngẫu nhiên client-side (demo). Trong thực tế: phải có key exchange.
    """
    def __init__(self, use_encryption=False):
        self.use_encryption = use_encryption and AES_AVAILABLE
        if self.use_encryption:
            self.key = get_random_bytes(16)  # 128-bit symmetric key (demo)
            # NOTE: no key-exchange implemented here; server must know key (for test, we could print)
            print("[SECURITY] AES available - using AES-128-CBC. Key (hex):", self.key.hex())
        else:
            self.key = None

    def encrypt(self, data):
        if not self.use_encryption:
            return data
        iv = get_random_bytes(16)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        # PKCS7 padding
        pad_len = 16 - (len(data) % 16)
        data_padded = data + bytes([pad_len]) * pad_len
        ct = cipher.encrypt(data_padded)
        return iv + ct

    def decrypt(self, data):
        if not self.use_encryption:
            return data
        iv = data[:16]
        ct = data[16:]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        pt_padded = cipher.decrypt(ct)
        pad_len = pt_padded[-1]
        return pt_padded[:-pad_len]


class X224Handshake:
    """
    Mô phỏng handshake X.224 (rất đơn giản)
    - Client gửi: TPKT + X224_CONNECT (simple bytes)
    - Server trả OK
    """
    CONNECT_MAGIC = b"X224_CONNECT_V1"
    CONFIRM_MAGIC = b"X224_CONFIRM_V1"

    def __init__(self, client_id, timeout=10):
        self.client_id = client_id
        self.timeout = timeout

    def do_handshake(self, sock):
        # send TPKT + connect payload
        payload = self.CONNECT_MAGIC + b":" + self.client_id.encode('utf-8')
        tpkt = struct.pack(TPKT_HEADER_FMT, 0x03, 0x00, TPKT_OVERHEAD + len(payload))
        sock.sendall(tpkt + payload)
        sock.settimeout(self.timeout)
        try:
            # expect a confirmation
            hdr = sock.recv(4)
            if len(hdr) < 4:
                return False
            ver, rsv, length = struct.unpack(TPKT_HEADER_FMT, hdr)
            body = sock.recv(length - 4)
            if body.startswith(self.CONFIRM_MAGIC):
                return True
            else:
                return False
        except Exception as e:
            print("[X224] handshake error:", e)
            return False


class MCSLite:
    """
    MCS-lite: chỉ gán 1 virtual channel id (ví dụ 1001) và gửi id trong control.
    Đây là mô phỏng đơn giản để tách kênh.
    """
    def __init__(self):
        self.channel_id = 1001

    def get_channel_id(self):
        return self.channel_id


class PDUBuilder:
    """Xây PDU: share control header + specific frame header + payload"""
    @staticmethod
    def build_full_frame_pdu(seq, jpeg_bytes, width, height, flags=0):
        ts_ms = int(time.time() * 1000)
        share_hdr = struct.pack(SHARE_CTRL_HDR_FMT, seq, ts_ms, PDU_TYPE_FULL, flags)
        frame_hdr = struct.pack(FRAME_FULL_HDR_FMT, width, height, len(jpeg_bytes))
        return share_hdr + frame_hdr + jpeg_bytes

    @staticmethod
    def build_rect_frame_pdu(seq, jpeg_bytes, x, y, w, h, full_width, full_height, flags=0):
        ts_ms = int(time.time() * 1000)
        share_hdr = struct.pack(SHARE_CTRL_HDR_FMT, seq, ts_ms, PDU_TYPE_RECT, flags)
        # We'll send rect header: x,y,w,h and also full image dimensions so server can place it
        # pack 5 ints: x,y,w,h,jpeg_len (we'll append jpeg bytes)
        rect_hdr = struct.pack(">IIIII", x, y, w, h, len(jpeg_bytes))
        full_dim = struct.pack(">II", full_width, full_height)
        return share_hdr + rect_hdr + full_dim + jpeg_bytes

    @staticmethod
    def build_control_pdu(seq, message_bytes):
        ts_ms = int(time.time() * 1000)
        share_hdr = struct.pack(SHARE_CTRL_HDR_FMT, seq, ts_ms, PDU_TYPE_CONTROL, 0)
        msg_len = struct.pack(">I", len(message_bytes))
        return share_hdr + msg_len + message_bytes


class ClientScreenSenderAdvanced:
    """
    Lớp chính gửi màn hình:
    - Nhận frame từ capturer thông qua enqueue_frame()
    - Nếu bbox != None và kích thước nhỏ hơn threshold -> crop và gửi rect PDU
    - Ngược lại gửi full frame PDU
    - Gói PDU vào TPKT, optional encrypt qua SecurityLayer
    - Handshake X.224 và MCS-lite trước khi gửi
    """
    def __init__(self, server_host, server_port, client_id,
                 use_encryption=False, rect_threshold_area=20000):
        self.server_host = server_host
        self.server_port = server_port
        self.client_id = client_id
        self.seq = 0
        self.queue = Queue(maxsize=2)
        self.stop_event = threading.Event()
        self.security = SecurityLayer(use_encryption=use_encryption)
        self.x224 = X224Handshake(client_id)
        self.mcs = MCSLite()
        # nếu vùng delta nhỏ hơn threshold -> gửi rect (tiết kiệm băng thông)
        self.rect_threshold_area = rect_threshold_area

    def enqueue_frame(self, width, height, jpg_bytes, bbox, pil_image):
        """
        Enqueue một frame hoặc region:
         - nếu bbox is None => enqueue full frame (jpg_bytes)
         - nếu bbox exists and area < rect_threshold_area => crop pil_image to bbox, re-encode to JPEG và enqueue rect
        """
        try:
            if bbox:
                left, upper, right, lower = bbox
                area = (right - left) * (lower - upper)
                if area > 0 and area <= self.rect_threshold_area:
                    # crop the PIL image and encode that crop to JPEG
                    rect_img = pil_image.crop((left, upper, right, lower))
                    bio = io.BytesIO()
                    rect_img.save(bio, format="JPEG", quality=75)
                    rect_jpg = bio.getvalue()
                    payload = {
                        "type": "rect",
                        "width": width,
                        "height": height,
                        "x": left,
                        "y": upper,
                        "w": right - left,
                        "h": lower - upper,
                        "jpg": rect_jpg
                    }
                else:
                    # send full
                    payload = {
                        "type": "full",
                        "width": width,
                        "height": height,
                        "jpg": jpg_bytes
                    }
            else:
                payload = {
                    "type": "full",
                    "width": width,
                    "height": height,
                    "jpg": jpg_bytes
                }

            # keep queue small and drop old if necessary (low-latency)
            if self.queue.full():
                try:
                    self.queue.get_nowait()
                except:
                    pass
            self.queue.put(payload)
        except Exception as e:
            print("[SENDER] enqueue_frame error:", e)

    def _pack_tpkt(self, data_bytes):
        total_len = TPKT_OVERHEAD + len(data_bytes)
        if total_len > MAX_TPKT_LENGTH:
            raise ValueError("TPKT frame too large: {}".format(total_len))
        tpkt_hdr = struct.pack(TPKT_HEADER_FMT, 0x03, 0x00, total_len)
        return tpkt_hdr + data_bytes

    def _send_via_socket(self, sock, data_bytes):
        # Apply security
        encrypted = self.security.encrypt(data_bytes)
        to_send = self._pack_tpkt(encrypted)
        sock.sendall(to_send)

    def send_loop(self):
        """
        Kết nối, do handshake, gửi frames từ queue.
        """
        while not self.stop_event.is_set():
            sock = None
            try:
                print(f"[SENDER] Connecting to {self.server_host}:{self.server_port} ...")
                sock = socket.create_connection((self.server_host, self.server_port), timeout=10)

                # Handshake X.224 (simple)
                ok = self.x224.do_handshake(sock)
                if not ok:
                    print("[SENDER] Handshake failed. Closing socket.")
                    sock.close()
                    time.sleep(3)
                    continue

                # After handshake, optionally inform channel id (MCS-lite)
                chan_msg = f"CHANNEL:{self.mcs.get_channel_id()}".encode("utf-8")
                chan_pdu = PDUBuilder.build_control_pdu(self.seq, chan_msg)
                self._send_via_socket(sock, chan_pdu)
                self.seq += 1

                # main send loop
                while not self.stop_event.is_set():
                    try:
                        payload = self.queue.get(timeout=1)
                        if payload["type"] == "full":
                            pdu = PDUBuilder.build_full_frame_pdu(self.seq, payload["jpg"], payload["width"], payload["height"])
                        else:
                            pdu = PDUBuilder.build_rect_frame_pdu(self.seq,
                                                                 payload["jpg"],
                                                                 payload["x"], payload["y"], payload["w"], payload["h"],
                                                                 payload["width"], payload["height"])
                        self._send_via_socket(sock, pdu)
                        self.seq += 1
                        print(f"[SENDER] sent seq={self.seq} type={payload['type']} bytes={len(pdu)}")
                    except Exception:
                        # timeout waiting for frames -> continue
                        pass
            except Exception as e:
                print("[SENDER] network error:", e)
                try:
                    if sock:
                        sock.close()
                except:
                    pass
                time.sleep(5)

    def stop(self):
        self.stop_event.set()
