from client.server.server_network.server_network import ServerNetwork
from client.server.server_network.server_broadcaster import ServerBroadcaster
from client.server.server_network.server_transport import ServerTransport
from client.common_network.mcs_layer import MCSLite
import time

class ServerApp:
    """Lớp điều phối toàn bộ server."""

    def __init__(self, host="0.0.0.0", port=9000):
        self.host = host
        self.port = port
        self.broadcaster = ServerBroadcaster()
        self.network = ServerNetwork(
            host, port,
            on_client_pdu=self.on_client_pdu,
            on_manager_conn=self.on_manager_conn
        )
        self.mcs = MCSLite()

    def start(self):
        print("[ServerApp] Starting server...")
        self.network.start()
        try:
            # tránh busy-loop 100% CPU
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("[ServerApp] Shutting down.")

    def on_manager_conn(self, manager_id, sock):
        self.broadcaster.add_manager(manager_id, sock)

    def on_client_pdu(self, session, pdu, raw_payload):
        """
        Xử lý khi nhận gói từ client.
        - session: ServerSession đối tượng nguồn
        - pdu: dict parsed từ PDU
        - raw_payload: chính xác payload (MCS packet) nhận được — có thể gửi trực tiếp đến managers
        """
        ch_name = pdu.get("channel")
        if ch_name == "screen":
            # raw_payload đã là MCS packet (2-byte channel id + PDU payload),
            # ServerTransport.send sẽ thêm TPKT header và gửi.
            for mid, conn in list(self.broadcaster.managers.items()):
                try:
                    ServerTransport.send(conn, raw_payload)
                except Exception:
                    print(f"[ServerApp] Manager {mid} disconnected.")
                    self.broadcaster.remove_manager(mid)
        else:
            print(f"[ServerApp] Unknown channel from {session.client_id}: {ch_name}")
