import cv2
import numpy as np
from client.manager.manager_network.manager_client import ManagerClient
from client.manager.manager_network.manager_transport import ManagerTransport
from client.common_network.pdu_parser import PDUParser

class ManagerApp:
    """Manager nhận frame từ server và hiển thị."""

    def __init__(self, server_host="127.0.0.1", server_port=9000, manager_id="manager1"):
        self.network = ManagerClient(server_host, server_port, manager_id)
        self.transport = ManagerTransport()
        self.parser = PDUParser()

    def start(self):
        print("[ManagerApp] Connecting...")
        if not self.network.connect():
            print("[ManagerApp] Connection failed.")
            return
        print("[ManagerApp] Connected.")
        self.network.recv_loop(self.on_data)

    def on_data(self, data: bytes):
        try:
            pdu = self.parser.parse_with_mcs(data)
            if pdu.get("channel") == "screen":
                img = cv2.imdecode(np.frombuffer(pdu["jpg"], np.uint8), cv2.IMREAD_COLOR)
                if img is None:
                    print("[ManagerApp] Failed to decode image")
                    return
                cv2.imshow("Remote Screen", img)
                cv2.waitKey(1)
        except Exception as e:
            print("[ManagerApp] Parse error:", e)
