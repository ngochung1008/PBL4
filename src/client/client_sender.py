# client_sender.py
import socket
import threading
import io
import time
from queue import Queue
import traceback
from common_network.pdu_builder import PDUBuilder
from common_network.tpkt_layer import TPKTLayer
from common_network.x224_handshake import X224Handshake
from common_network.pdu_parser import PDUParser
import json
import pyautogui  # used for applying input actions

class ClientScreenSender:
    def __init__(self, host, port, client_id, use_encryption=False, rect_threshold_area=20000):
        self.host = host
        self.port = port
        self.client_id = client_id
        self.seq = 0
        self.queue = Queue(maxsize=4)
        self.stop_event = threading.Event()
        self.rect_threshold_area = rect_threshold_area
        self.sock = None
        self.parser = PDUParser()

    def enqueue_frame(self, width, height, jpg_bytes, bbox, pil_image):
        try:
            if bbox:
                left, upper, right, lower = bbox
                area = (right-left)*(lower-upper)
                if area <= self.rect_threshold_area:
                    payload = {"type":"rect","width":width,"height":height,"x":left,"y":upper,"w":right-left,"h":lower-upper,"jpg":jpg_bytes}
                else:
                    payload = {"type":"full","width":width,"height":height,"jpg":jpg_bytes}
            else:
                payload = {"type":"full","width":width,"height":height,"jpg":jpg_bytes}
            if self.queue.full():
                try: self.queue.get_nowait()
                except: pass
            self.queue.put(payload)
        except Exception as e:
            print("[SENDER] enqueue_frame error:", e)

    def _send_raw(self, bts):
        self.sock.sendall(TPKTLayer.pack(bts))

    def start(self):
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        while not self.stop_event.is_set():
            try:
                self.sock = socket.create_connection((self.host, self.port), timeout=10)
                # handshake
                X224Handshake.client_send_connect(self.sock, self.client_id)
                print("[CLIENT] connected & handshake done")
                # send initial control: channel id (optional)
                chan_msg = ("CHANNEL:SCREEN").encode()
                ctrl = PDUBuilder.build_control_pdu(self.seq, chan_msg)
                self._send_raw(ctrl); self.seq += 1

                # start receiver thread to accept input PDUs
                threading.Thread(target=self._recv_loop, daemon=True).start()

                # send loop
                while not self.stop_event.is_set():
                    try:
                        payload = self.queue.get(timeout=1)
                    except Exception:
                        continue
                    if payload["type"] == "full":
                        pdu = PDUBuilder.build_full_frame_pdu(self.seq, payload["jpg"], payload["width"], payload["height"])
                    else:
                        pdu = PDUBuilder.build_rect_frame_pdu(self.seq, payload["jpg"],
                            payload["x"], payload["y"], payload["w"], payload["h"],
                            payload["width"], payload["height"])
                    self._send_raw(pdu)
                    print(f"[CLIENT] sent seq={self.seq} type={payload['type']} size={len(pdu)}")
                    self.seq += 1
            except Exception as e:
                print("[CLIENT] network error:", e)
                traceback.print_exc()
                try:
                    if self.sock:
                        self.sock.close()
                except:
                    pass
                time.sleep(3)

    def _recv_loop(self):
        try:
            while not self.stop_event.is_set():
                hdr = X224Handshake.recv_all(self.sock, 4)
                ver, rsv, length = TPKTLayer.unpack_header(hdr)
                body = X224Handshake.recv_all(self.sock, length - 4)
                pdu = self.parser.parse(body)
                if pdu["type"] == "input":
                    inp = pdu.get("input") or {}
                    # apply input (excluding client_id field)
                    self.apply_input(inp)
        except Exception as e:
            print("[CLIENT] recv loop ended:", e)

    def apply_input(self, inp):
        """
        inp format example (from manager):
        {
          "client_id": "client01",
          "type": "mouse",
          "action": "move",
          "x": 100,
          "y": 200,
          "button": "left"
        }
        or keyboard:
        {
          "client_id":"client01",
          "type":"keyboard","action":"down","key":"a"
        }
        """
        try:
            if not inp or 'type' not in inp:
                return
            itype = inp['type']
            if itype == 'mouse':
                action = inp.get('action')
                x = inp.get('x'); y = inp.get('y')
                # x,y are absolute in client's screen space (manager must send scaled coords)
                if action == 'move':
                    pyautogui.moveTo(x, y)
                elif action == 'click':
                    btn = inp.get('button','left')
                    pyautogui.click(x, y, button=btn)
                elif action == 'down':
                    pyautogui.mouseDown(x, y, button=inp.get('button','left'))
                elif action == 'up':
                    pyautogui.mouseUp(x, y, button=inp.get('button','left'))
            elif itype == 'keyboard':
                action = inp.get('action')
                key = inp.get('key')
                if action == 'down':
                    pyautogui.keyDown(key)
                elif action == 'up':
                    pyautogui.keyUp(key)
                elif action == 'press':
                    pyautogui.press(key)
        except Exception as e:
            print("[CLIENT] apply_input error:", e)

    def stop(self):
        self.stop_event.set()
        try:
            if self.sock:
                self.sock.close()
        except:
            pass
