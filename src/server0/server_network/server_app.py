# server0/server_network/server_app.py

from server0.server_network.server_network import ServerNetwork
from server0.server_network.server_broadcaster import ServerBroadcaster
from server0.server_network.server_session_manager import SessionManager

class ServerApp:
    def __init__(self, host="0.0.0.0", port=5000, certfile=None, keyfile=None):
        
        # 1. Khởi tạo Broadcaster (Gửi tin nhắn)
        self.broadcaster = ServerBroadcaster()
        
        # 2. Khởi tạo Session Manager (Logic chính)
        self.session_manager = SessionManager(self.broadcaster)
        
        # 3. Khởi tạo Network (Nhận kết nối)
        self.network = ServerNetwork(
            host=host, 
            port=port, 
            certfile=certfile, 
            keyfile=keyfile
        )
        
        # --- Kết nối các thành phần ---
        
        # Cung cấp cho Network các hàm callback từ SessionManager
        # để xử lý khi có kết nối, PDU, hoặc mất kết nối.
        self.network.set_callbacks(
            on_connect=self.session_manager.handle_new_connection,
            on_pdu=self.session_manager.handle_pdu,
            on_disconnect=self.session_manager.handle_disconnection
        )
        
        # Cung cấp Broadcaster cho Network (để đăng ký client)
        self.network.set_broadcaster(self.broadcaster)

    def start(self):
        print("[ServerApp] Đang khởi động các dịch vụ...")
        self.broadcaster.start()
        self.session_manager.start()
        self.network.start()
        print("[ServerApp] Server đã sẵn sàng.")

    def stop(self):
        print("[ServerApp] Đang dừng các dịch vụ...")
        self.network.stop()
        self.session_manager.stop()
        self.broadcaster.stop()
        print("[ServerApp] Đã dừng hoàn toàn.")