# manager/manager_viewer.py

import threading
from PIL import Image
import io
import time
from typing import Optional, Dict, Any, Tuple

class ManagerViewer:
    """
    Quản lý ảnh nền (base image) và xử lý logic vá (patch) các vùng thay đổi.
    """

    def __init__(self):
        self.lock = threading.Lock()
        # Lưu trữ ảnh nền đầy đủ (base image)
        self.current_base_image: Dict[str, Optional[Image.Image]] = {} 
        self.current_base_size: Dict[str, Tuple[int, int]] = {}
        
    def process_video_pdu(self, client_id: str, pdu: dict) -> Optional[Image.Image]:
        """
        Xử lý PDU video (full/rect), vá ảnh nếu cần, và trả về ảnh nền mới nhất.
        """
        jpg = pdu.get("jpg")
        ptype = pdu.get("type")
        
        if not jpg: 
            return None
        
        try:
            # Giải mã JPEG của vùng/ảnh mới
            # Rất quan trọng: Sử dụng io.BytesIO để giải mã in-memory
            new_img = Image.open(io.BytesIO(jpg)).convert("RGB")
        except Exception as e:
            # Nếu giải mã lỗi (ảnh hỏng), bỏ qua frame này
            print(f"[ManagerViewer] Lỗi giải mã JPEG: {e}")
            return None

        with self.lock:
            current_base = self.current_base_image.get(client_id)
            
            # --- XỬ LÝ PDU FULL (LÀM MỚI TOÀN BỘ) ---
            if ptype == "full":
                print(f"[Viewer] Nhận FULL Frame size: {new_img.size}")
                self.current_base_image[client_id] = new_img
                self.current_base_size[client_id] = new_img.size
                return new_img.copy() 
            
            # --- XỬ LÝ PDU RECT (VÁ ẢNH) ---
            elif ptype == "rect":
                x, y, w, h = pdu.get("x"), pdu.get("y"), pdu.get("w"), pdu.get("h")
                full_w, full_h = pdu.get("full_w"), pdu.get("full_h")

                # 1. Kiểm tra ảnh nền: NẾU THIẾU HOẶC KHÔNG KHỚP KÍCH THƯỚC -> BỎ QUA RECT
                if current_base is None or current_base.size != (full_w, full_h):
                    print(f"[Viewer] Bỏ qua RECT: Thiếu Base Image hoặc size thay đổi ({current_base.size if current_base else 'None'} -> {full_w}x{full_h}). Cần PDU FULL.")
                    return None # Bỏ qua frame RECT này
                    
                # 2. Vá (paste) vùng thay đổi lên ảnh nền
                try:
                    # new_img: Vùng ảnh JPEG đã được cắt
                    current_base.paste(new_img, (x, y))
                except ValueError as e:
                    print(f"[Viewer] Lỗi vá ảnh: {e}. Bỏ qua frame RECT.")
                    return None

                # 3. Trả về ảnh đã vá
                return current_base.copy()
            
            return current_base.copy() if current_base else None

    def clear_frames(self):
        with self.lock:
            self.current_base_image.clear()
            self.current_base_size.clear()
            
    def stop(self):
        self.clear_frames()