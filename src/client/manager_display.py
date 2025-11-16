from PIL import Image
import io

class ManagerDisplay:
    def __init__(self):
        self.last_frame = None

    def render(self, pdu):
        """Hiển thị khung hình hoặc cập nhật delta."""
        ptype = pdu.get("type")
        if ptype == "full":
            self.show_jpeg(pdu["jpg"])
        elif ptype == "rect":
            self.show_jpeg(pdu["jpg"], pdu["x"], pdu["y"])
        elif ptype == "control":
            print("[MANAGER] Control:", pdu["message"])
        else:
            print("[MANAGER] Unknown PDU type:", ptype)

    def show_jpeg(self, jpg_bytes, x=0, y=0):
        img = Image.open(io.BytesIO(jpg_bytes))
        img.show()
