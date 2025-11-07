# manager_sender.py
import socket, threading, time
from common_network.x224_handshake import X224Handshake
from common_network.tpkt_layer import TPKTLayer
from common_network.pdu_builder import PDUBuilder

class ManagerSender:
    def __init__(self, host, port, manager_id="manager1"):
        self.host = host
        self.port = port
        self.manager_id = manager_id
        self.sock = None
        self.seq = 0
        self.lock = threading.Lock()
        self.connected = False

    def connect(self):
        self.sock = socket.create_connection((self.host, self.port), timeout=10)
        X224Handshake.client_send_connect(self.sock, self.manager_id)
        # Optionally send CONTROL channel message
        chan_msg = ("CHANNEL:INPUT").encode()
        ctrl = PDUBuilder.build_control_pdu(self.seq, chan_msg)
        self.sock.sendall(TPKTLayer.pack(ctrl)); self.seq += 1
        self.connected = True
        # keepalive thread optional
        threading.Thread(target=self._keepalive, daemon=True).start()

    def _keepalive(self):
        while self.connected:
            time.sleep(30)
            try:
                ping = PDUBuilder.build_control_pdu(self.seq, b"PING")
                self.sock.sendall(TPKTLayer.pack(ping)); self.seq += 1
            except Exception:
                self.connected = False

    def send_input(self, input_obj):
        # Ensure input_obj contains "client_id"
        if not self.connected:
            raise RuntimeError("Not connected")
        with self.lock:
            pdu = PDUBuilder.build_input_pdu(self.seq, input_obj)
            self.sock.sendall(TPKTLayer.pack(pdu))
            self.seq += 1

    def close(self):
        self.connected = False
        try: self.sock.close()
        except: pass
