"""
ServerApp
- Nhận kết nối từ client
- Giải mã PDU, relay sang manager
"""

import threading
from server_network.server_session import ServerSession

class ServerApp:
    def __init__(self, host="0.0.0.0", port=8443):
        self.host = host
        self.port = port
        self.session = ServerSession(host, port)
        self.running = True

    def start(self):
        print(f"[SERVER] Listening on {self.host}:{self.port}")
        self.session.start_accept_loop()

    def stop(self):
        self.session.stop = True
        print("[SERVER] Stopped.")

if __name__ == "__main__":
    app = ServerApp()
    try:
        app.start()
    except KeyboardInterrupt:
        app.stop()
