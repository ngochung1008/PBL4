# manager_network/manager_receiver.py
import threading
from client.manager.manager_network.manager_transport import ManagerTransport
from client.common_network.pdu_parser import PDUParser

class ManagerReceiver(threading.Thread):
    """Luồng nhận dữ liệu (frame) từ server."""

    def __init__(self, sock, on_frame_callback):
        super().__init__(daemon=True)
        self.sock = sock
        self.running = True
        self.transport = ManagerTransport()
        self.parser = PDUParser()
        self.on_frame_callback = on_frame_callback

    def run(self):
        while self.running:
            try:
                data = self.transport.recv(self.sock)
                pdu = self.parser.parse_with_mcs(data)
                if pdu["channel"] == "screen":
                    self.on_frame_callback(pdu["jpg"])
            except Exception as e:
                print("[ManagerReceiver] Error:", e)
                self.running = False
                break

    def stop(self):
        self.running = False
