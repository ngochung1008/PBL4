import threading
from client.server.server_network.server_transport import ServerTransport

class ServerBroadcaster:
    def __init__(self):
        self.managers = {}  # id -> socket/connection
        self.lock = threading.Lock()

    def add_manager(self, manager_id, conn):
        with self.lock:
            self.managers[manager_id] = conn

    def remove_manager(self, manager_id):
        with self.lock:
            if manager_id in self.managers:
                del self.managers[manager_id]

    def broadcast(self, data: bytes):
        with self.lock:
            for mid, conn in list(self.managers.items()):
                try:
                    ServerTransport.send(conn, data)
                except Exception:
                    print(f"[Broadcaster] Remove dead manager {mid}")
                    del self.managers[mid]
