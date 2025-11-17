import threading
from queue import Queue, Empty
from common_network.tpkt_layer import TPKTLayer

class ServerBroadcaster(threading.Thread):
    """
    Nhận (target_id, mcs_frame) từ queue, đóng gói TPKT và gửi đi.
    mcs_frame: đã bao gồm (channel header + pdu payload).
    """
    def __init__(self):
        super().__init__(daemon=True, name="Broadcaster")
        self.running = True
        self.queue = Queue(maxsize=1024) # Giới hạn queue để tránh OOM
        self.clients = {}  # client_id -> ssl_socket
        self.lock = threading.Lock()

    def register(self, client_id: str, ssl_sock):
        with self.lock:
            self.clients[client_id] = ssl_sock
        print(f"[Broadcaster] Đã đăng ký {client_id}")

    def unregister(self, client_id: str):
        with self.lock:
            self.clients.pop(client_id, None)
        print(f"[Broadcaster] Đã hủy đăng ký {client_id}")

    def enqueue(self, target_id: str, mcs_frame: bytes):
        """Đưa (người nhận, dữ liệu MCS) vào hàng đợi"""
        if not self.running:
            return
        try:
            self.queue.put((target_id, mcs_frame), block=False)
        except Queue.Full:
            print(f"[Broadcaster] Hàng đợi gửi bị đầy! Bỏ qua gói tin cho {target_id}")

    def run(self):
        while self.running:
            try:
                target_id, mcs_frame = self.queue.get(timeout=0.5)
            except Empty:
                continue

            ssl_sock = None
            with self.lock:
                ssl_sock = self.clients.get(target_id)

            if ssl_sock:
                try:
                    # --- Đóng gói TPKT và gửi ---
                    tpkt_packet = TPKTLayer.pack(mcs_frame)
                    ssl_sock.sendall(tpkt_packet)
                    
                except Exception as e:
                    # Nếu gửi lỗi (ví dụ: client ngắt kết nối)
                    # ServerReceiver sẽ tự phát hiện và dọn dẹp
                    # Chúng ta chỉ cần log lỗi
                    print(f"[Broadcaster] Lỗi khi gửi cho {target_id}: {e}")
                    # Không cần unregister ở đây, để Receiver/Network xử lý

    def stop(self):
        self.running = False
        print("[Broadcaster] Đang dừng...")
        with self.queue.mutex:
            self.queue.queue.clear()
        with self.lock:
            self.clients.clear()
        print("[Broadcaster] Đã dừng.")