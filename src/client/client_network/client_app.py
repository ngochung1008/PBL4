from client.client_network import ClientNetwork
from client.client_sender import ClientSender
from client.client_screenshot import ClientScreenshot
from client.common_network.mcs_layer import MCSLite

class ClientApp:
    def __init__(self, host, port, client_id="client1"):
        self.network = ClientNetwork(host, port, client_id)
        self.mcs = MCSLite()
        self.sender = None
        self.capturer = None

    def start(self):
        if not self.network.connect():
            print("[ClientApp] Connect failed.")
            return
        self.sender = ClientSender(self.network.sock, self.mcs, fps=2)
        self.sender.start()

        self.capturer = ClientScreenshot(fps=2)
        self.capturer.capture_loop(self._on_frame)

    def _on_frame(self, w, h, jpg, bbox, img, seq, ts_ms):
        self.sender.enqueue_frame(w, h, jpg, bbox, seq, ts_ms)
