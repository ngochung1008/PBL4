import threading
import queue
import time
from client.client_network.client_transport import ClientTransport
from client.common_network.mcs_layer import MCSLite
from client.common_network.pdu_builder import PDUBuilder

class ClientSender(threading.Thread):
    """
    Luồng gửi frame đến server.
    - Nhận frame từ hàng đợi (queue)
    - Gửi qua socket đã kết nối
    """

    def __init__(self, sock, mcs: MCSLite = None, fps=2):
        super().__init__(daemon=True)
        self.sock = sock
        self.mcs = mcs if mcs is not None else MCSLite()
        self.queue = queue.Queue(maxsize=10)
        self.running = True
        self.fps = fps
        self.transport = ClientTransport()
        self._seq = 1

    def enqueue_frame(self, width, height, jpg_bytes, bbox=None, seq=None, ts_ms=None):
        """Thêm frame vào queue (nếu còn chỗ)."""
        if not self.running:
            return
        try:
            # allow external seq/ts or use internal
            if seq is None:
                seq = self._seq
                self._seq += 1
            if ts_ms is None:
                ts_ms = int(time.time() * 1000)
            self.queue.put_nowait((width, height, jpg_bytes, bbox, seq, ts_ms))
        except queue.Full:
            print("[ClientSender] Queue full, dropping frame.")

    def run(self):
        """Loop gửi dữ liệu."""
        while self.running:
            try:
                width, height, jpg, bbox, seq, ts = self.queue.get(timeout=1)
                # Decide PDU type: full frame for simplicity (you can add rect handling)
                pdu_payload = PDUBuilder.build_full_frame_pdu(seq, jpg, width, height, flags=0)
                # Wrap with MCS
                mcs_packet = self.mcs.pack("screen", pdu_payload)
                # Send via transport (TPKT)
                self.transport.send(self.sock, mcs_packet)
            except queue.Empty:
                continue
            except Exception as e:
                print("[ClientSender] Error sending:", e)
                self.running = False
                break

    def stop(self):
        self.running = False
