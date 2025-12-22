"""
Screenshot Storage Module
Lưu trữ screenshots từ client theo cấu trúc: client_name/year/month/day/image_name.jpg
"""

import os
import io
from datetime import datetime
from pathlib import Path
from typing import Optional
from PIL import Image
import struct


class ScreenshotStorage:
    """Quản lý việc lưu trữ screenshots từ client"""
    
    def __init__(self, base_path: str = "screenshots", change_threshold: int = 20000):
        """
        Khởi tạo storage
        
        Args:
            base_path: Đường dẫn thư mục gốc để lưu screenshots (mặc định: screenshots/)
            change_threshold: Ngưỡng thay đổi để lưu screenshot (số pixel thay đổi, mặc định: 20000)
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Theo dõi base image cho mỗi client để ghép RECT
        self.client_base_images = {}  # {client_name: PIL.Image}
        self.client_last_save_time = {}  # {client_name: datetime}
        self.change_threshold = change_threshold  # Ngưỡng thay đổi để lưu
        
        print(f"[ScreenshotStorage] Initialized with base path: {self.base_path.absolute()}")
        print(f"[ScreenshotStorage] Change threshold: {change_threshold} pixels")
    
    def _get_storage_path(self, client_name: str, timestamp: Optional[datetime] = None) -> Path:
        """
        Tạo đường dẫn lưu trữ theo cấu trúc: client_name/year/month/day/
        
        Args:
            client_name: Tên client (username)
            timestamp: Thời điểm chụp (mặc định: hiện tại)
        
        Returns:
            Path object của thư mục lưu trữ
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        # Tạo cấu trúc thư mục: client_name/year/month/day/
        year = timestamp.strftime("%Y")
        month = timestamp.strftime("%m")
        day = timestamp.strftime("%d")
        
        storage_path = self.base_path / client_name / year / month / day
        storage_path.mkdir(parents=True, exist_ok=True)
        
        return storage_path
    
    def _generate_filename(self, timestamp: Optional[datetime] = None, prefix: str = "screen") -> str:
        """
        Tạo tên file cho screenshot
        
        Args:
            timestamp: Thời điểm chụp (mặc định: hiện tại)
            prefix: Tiền tố của file (mặc định: "screen")
        
        Returns:
            Tên file với định dạng: screen_HHMMSS.jpg
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        # Format: screen_145030.jpg (giờ phút giây)
        time_str = timestamp.strftime("%H%M%S")
        
        return f"{prefix}_{time_str}.jpg"
    
    def save_screenshot_from_pdu(self, client_name: str, pdu: dict) -> Optional[str]:
        """
        Lưu screenshot từ PDU (type = "full" hoặc "rect")
        
        Args:
            client_name: Tên client (username)
            pdu: PDU chứa dữ liệu ảnh
        
        Returns:
            Đường dẫn file đã lưu hoặc None nếu lỗi
        """
        try:
            pdu_type = pdu.get("type")
            
            # Chỉ lưu PDU type FULL (ảnh đầy đủ), bỏ qua RECT (ảnh patch)
            if pdu_type != "full":
                return None
            
            # Lấy dữ liệu JPG từ PDU
            jpg_data = pdu.get("jpg")
            if not jpg_data:
                print(f"[ScreenshotStorage] WARN: No jpg data in PDU from {client_name}")
                return None
            
            # Tạo timestamp
            timestamp = datetime.now()
            
            # Lấy đường dẫn thư mục
            storage_path = self._get_storage_path(client_name, timestamp)
            
            # Tạo tên file
            filename = self._generate_filename(timestamp)
            
            # Đường dẫn đầy đủ
            file_path = storage_path / filename
            
            # Lưu file
            with open(file_path, 'wb') as f:
                f.write(jpg_data)
            
            print(f"[ScreenshotStorage] ✓ Saved screenshot: {file_path}")
            return str(file_path)
            
        except Exception as e:
            print(f"[ScreenshotStorage] ERROR saving screenshot: {e}")
            return None
    
    def save_screenshot_from_raw(self, client_name: str, raw_payload: bytes) -> Optional[str]:
        """
        Lưu screenshot từ raw payload (TPKT/MCS/PDU đầy đủ)
        Hỗ trợ cả FULL và RECT frames
        
        Args:
            client_name: Tên client (username)
            raw_payload: Raw bytes của PDU
        
        Returns:
            Đường dẫn file đã lưu hoặc None nếu không lưu
        """
        try:
            # Parse header để lấy type
            if len(raw_payload) < 14:  # Share header = 14 bytes
                return None
            
            # Read header: seq (4), timestamp (8), type (1), flags (1)
            seq, ts_ms, ptype, flags = struct.unpack_from(">IQBB", raw_payload)
            offset = 14
            
            # XỬ LÝ FULL FRAME (type = 1)
            if ptype == 1:
                # Read FULL header: w (4), h (4), jpg_len (4)
                if len(raw_payload) < offset + 12:
                    return None
                
                w, h, jpg_len = struct.unpack_from(">III", raw_payload, offset)
                offset += 12
                
                # Extract JPG data
                if len(raw_payload) < offset + jpg_len:
                    return None
                
                jpg_data = raw_payload[offset:offset + jpg_len]
                
                # Lưu làm base image
                try:
                    base_img = Image.open(io.BytesIO(jpg_data)).convert("RGB")
                    self.client_base_images[client_name] = base_img
                    print(f"[ScreenshotStorage] Updated base image for {client_name}: {w}x{h}")
                except Exception as e:
                    print(f"[ScreenshotStorage] ERROR loading base image: {e}")
                    return None
                
                # Lưu FULL frame (luôn lưu để có base image)
                return self._save_image(client_name, base_img, force=True)
            
            # XỬ LÝ RECT FRAME (type = 2)
            elif ptype == 2:
                # Read RECT header: x (4), y (4), w (4), h (4), jpg_len (4)
                if len(raw_payload) < offset + 20:
                    return None
                
                x, y, rect_w, rect_h, jpg_len = struct.unpack_from(">IIIII", raw_payload, offset)
                offset += 20
                
                # Read full_w, full_h
                if len(raw_payload) < offset + 8:
                    return None
                
                full_w, full_h = struct.unpack_from(">II", raw_payload, offset)
                offset += 8
                
                # Extract JPG data
                if len(raw_payload) < offset + jpg_len:
                    return None
                
                jpg_data = raw_payload[offset:offset + jpg_len]
                
                # GIẢI PHÁP: Lưu RECT frame độc lập (không cần base image)
                # Vì mục đích giám sát, ta chỉ cần lưu các frame thay đổi
                # Không nhất thiết phải ghép thành ảnh hoàn chỉnh
                
                # Kiểm tra có base image không - nếu có thì ghép, không có thì lưu riêng
                if client_name not in self.client_base_images:
                    print(f"[ScreenshotStorage] No base image for {client_name}, saving RECT independently")
                    # Lưu RECT frame riêng lẻ
                    try:
                        rect_img = Image.open(io.BytesIO(jpg_data)).convert("RGB")
                        return self._save_image(client_name, rect_img, force=True, prefix=f"rect_{x}_{y}")
                    except Exception as e:
                        print(f"[ScreenshotStorage] ERROR saving RECT independently: {e}")
                        return None
                
                base_img = self.client_base_images[client_name]
                
                # Kiểm tra kích thước có khớp không
                if base_img.size != (full_w, full_h):
                    print(f"[ScreenshotStorage] Size mismatch for {client_name}, clearing base")
                    del self.client_base_images[client_name]
                    return None
                
                # Ghép RECT vào base image
                try:
                    rect_img = Image.open(io.BytesIO(jpg_data)).convert("RGB")
                    
                    # Tạo bản copy của base image
                    updated_img = base_img.copy()
                    updated_img.paste(rect_img, (x, y))
                    
                    # Cập nhật base image
                    self.client_base_images[client_name] = updated_img
                    
                    # Tính diện tích thay đổi
                    changed_pixels = rect_w * rect_h
                    
                    # DEBUG: Luôn hiển thị thông tin RECT
                    print(f"[ScreenshotStorage] RECT for {client_name}: {rect_w}x{rect_h} at ({x},{y}) = {changed_pixels} pixels")
                    
                    # LƯU MỌI FRAME - LUÔN LƯU KHI THRESHOLD = 0
                    if self.change_threshold == 0:
                        # Threshold = 0 → LƯU NGAY, không cần kiểm tra gì
                        print(f"[ScreenshotStorage] 💾 Threshold=0 → Saving ALL frames unconditionally")
                        result = self._save_image(client_name, updated_img, force=True)
                        if result:
                            print(f"[ScreenshotStorage] ✅ RECT saved: {result}")
                        return result
                    elif changed_pixels >= self.change_threshold:
                        # Threshold > 0 → Kiểm tra diện tích thay đổi
                        print(f"[ScreenshotStorage] ✅ Change > threshold ({changed_pixels} >= {self.change_threshold}), attempting save...")
                        result = self._save_image(client_name, updated_img, force=False)
                        if result:
                            print(f"[ScreenshotStorage] ✅ Screenshot saved successfully")
                        else:
                            print(f"[ScreenshotStorage] ⚠️ Screenshot not saved (throttled)")
                        return result
                    else:
                        # Thay đổi nhỏ, không lưu (chỉ khi threshold > 0)
                        print(f"[ScreenshotStorage] ❌ Change < threshold ({changed_pixels} < {self.change_threshold}), skipping save")
                        return None
                    
                except Exception as e:
                    print(f"[ScreenshotStorage] ERROR merging RECT: {e}")
                    return None
            
            else:
                # Loại PDU khác, không xử lý
                return None
                
        except Exception as e:
            print(f"[ScreenshotStorage] ERROR saving screenshot from raw: {e}")
            return None
    
    def _save_image(self, client_name: str, img: Image.Image, force: bool = False, prefix: str = "screen") -> Optional[str]:
        """
        Lưu image vào disk
        
        Args:
            client_name: Tên client
            img: PIL Image object
            force: Bắt buộc lưu (bỏ qua throttling)
            prefix: Tiền tố cho tên file (mặc định: "screen")
        
        Returns:
            Đường dẫn file đã lưu hoặc None
        """
        try:
            # Bỏ THROTTLING - LƯU MỌI FRAME
            # (Comment out throttling code to save every frame)
            
            # Tạo timestamp
            timestamp = datetime.now()
            
            # Lấy đường dẫn thư mục
            storage_path = self._get_storage_path(client_name, timestamp)
            
            # Tạo tên file đơn giản: screen_HHMMSS.jpg hoặc rect_x_y_HHMMSS.jpg
            filename = self._generate_filename(timestamp, prefix=prefix)
            
            # Đường dẫn đầy đủ
            file_path = storage_path / filename
            
            # Kiểm tra file đã tồn tại chưa (tránh ghi đè nếu cùng giây)
            counter = 1
            original_filename = filename
            while file_path.exists():
                # Thêm suffix _1, _2, ... nếu trùng
                name_without_ext = original_filename.replace(".jpg", "")
                filename = f"{name_without_ext}_{counter}.jpg"
                file_path = storage_path / filename
                counter += 1
            
            # Lưu file
            img.save(file_path, format='JPEG', quality=85, optimize=True)
            
            # Cập nhật last save time
            self.client_last_save_time[client_name] = timestamp
            
            print(f"[ScreenshotStorage] ✓ Saved screenshot: {file_path}")
            return str(file_path)
            
        except Exception as e:
            print(f"[ScreenshotStorage] ERROR saving image: {e}")
            return None
    
    def get_client_screenshots(self, client_name: str, date: Optional[datetime] = None) -> list:
        """
        Lấy danh sách screenshots của client theo ngày
        
        Args:
            client_name: Tên client
            date: Ngày cần lấy (mặc định: hôm nay)
        
        Returns:
            List các đường dẫn file
        """
        if date is None:
            date = datetime.now()
        
        storage_path = self._get_storage_path(client_name, date)
        
        if not storage_path.exists():
            return []
        
        # Lấy tất cả file .jpg trong thư mục
        screenshots = list(storage_path.glob("*.jpg"))
        return [str(s) for s in sorted(screenshots)]
    
    def get_all_client_names(self) -> list:
        """
        Lấy danh sách tất cả client đã được lưu screenshot
        
        Returns:
            List tên client
        """
        if not self.base_path.exists():
            return []
        
        # Lấy tất cả thư mục con (mỗi thư mục là tên client)
        client_dirs = [d.name for d in self.base_path.iterdir() if d.is_dir()]
        return sorted(client_dirs)
    
    def cleanup_old_screenshots(self, days: int = 30):
        """
        Xóa screenshots cũ hơn số ngày chỉ định
        
        Args:
            days: Số ngày để giữ lại (mặc định: 30)
        """
        from datetime import timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        deleted_count = 0
        for client_dir in self.base_path.iterdir():
            if not client_dir.is_dir():
                continue
            
            # Duyệt qua year/month/day
            for year_dir in client_dir.iterdir():
                if not year_dir.is_dir():
                    continue
                for month_dir in year_dir.iterdir():
                    if not month_dir.is_dir():
                        continue
                    for day_dir in month_dir.iterdir():
                        if not day_dir.is_dir():
                            continue
                        
                        # Parse date từ path
                        try:
                            date_str = f"{year_dir.name}-{month_dir.name}-{day_dir.name}"
                            dir_date = datetime.strptime(date_str, "%Y-%m-%d")
                            
                            if dir_date < cutoff_date:
                                # Xóa thư mục và tất cả file bên trong
                                for file in day_dir.glob("*.jpg"):
                                    file.unlink()
                                    deleted_count += 1
                                
                                # Xóa thư mục rỗng
                                try:
                                    day_dir.rmdir()
                                    month_dir.rmdir()
                                    year_dir.rmdir()
                                except OSError:
                                    pass  # Thư mục không rỗng
                        except ValueError:
                            continue
        
        if deleted_count > 0:
            print(f"[ScreenshotStorage] Cleaned up {deleted_count} old screenshots")
