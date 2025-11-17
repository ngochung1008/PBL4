import threading
from PIL import Image
import io
import time

class ManagerViewer:
    """
    Lưu trữ frame ảnh PIL mới nhất cho mỗi client_id.
    """

    def __init__(self):
        self.frames = {}  # client_id -> (PIL.Image, ts_ms)
        self.lock = threading.Lock()

    def handle_frame_pdu(self, client_id: str, pdu: dict):
        """
        Được gọi bởi lớp Manager, truyền vào client_id của phiên.
        """
        jpg = pdu.get("jpg")
        if not jpg:
            return
            
        try:
            # Giải mã JPEG
            img = Image.open(io.BytesIO(jpg)).convert("RGB")
        except Exception as e:
            print(f"[ManagerViewer] Lỗi giải mã JPEG cho {client_id}: {e}")
            return

        ts = pdu.get("ts_ms", int(time.time() * 1000))

        with self.lock:
            # Lưu frame mới nhất
            self.frames[client_id] = (img, ts)

    def get_latest_frame(self, client_id: str):
        with self.lock:
            return self.frames.get(client_id)

    def clear_frames(self):
        with self.lock:
            self.frames.clear()
            
    def stop(self):
        self.clear_frames()