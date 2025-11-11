import threading
from client_network import ClientNetwork
from client_sender import ClientSender
from client_input_handler import ClientInputHandler
from client_screenshot import ClientScreenshot

class ClientApp:
    """Quản lý toàn bộ client: chụp màn hình, gửi frame, nhận input"""
    def __init__(self, server_host="127.0.0.1", server_port=8443, client_id="client_01"):
        self.network = ClientNetwork(server_host, server_port, client_id)
        self.sender = ClientSender(self.network)
        self.screenshot = ClientScreenshot(fps=2, quality=75, max_dimension=1280)
        self.input_handler = ClientInputHandler(self.network)
        self.running = True

    def start(self):
        print("[CLIENT] Connecting to server...")
        self.network.connect()

        # Bắt đầu luồng nhận input từ server
        t_input = threading.Thread(target=self.input_handler.handle_loop, daemon=True)
        t_input.start()

        # Callback nhận ảnh chụp từ ClientScreenshot
        def on_capture(width, height, jpg_bytes, bbox, pil_img, seq, ts_ms):
            # Gửi frame kèm seq và timestamp
            self.sender.send_frame(width, height, jpg_bytes, bbox, seq, ts_ms)

        print("[CLIENT] Starting capture loop...")
        self.screenshot.capture_loop(on_capture)

    def stop(self):
        self.screenshot.stop = True
        self.input_handler.running = False
        self.network.close()

if __name__ == "__main__":
    app = ClientApp()
    try:
        app.start()
    except KeyboardInterrupt:
        app.stop()
        print("\n[CLIENT] Stopped.")
