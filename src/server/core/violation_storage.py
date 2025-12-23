# server/core/violation_storage.py
"""
Violation Storage - Lưu trữ screenshots vi phạm từ AI Monitor
Mỗi violation screenshot sẽ được lưu vào thư mục riêng với metadata
"""

import os
import json
from datetime import datetime
import threading


class ViolationStorage:
    """
    Quản lý lưu trữ screenshots vi phạm bảo mật
    Cấu trúc thư mục:
    violations/
        └── {username}/
            └── {year}/
                └── {month}/
                    └── {violation_type}/
                        ├── {timestamp}.jpg
                        └── {timestamp}.json  (metadata)
    """
    
    def __init__(self, base_path="violations"):
        self.base_path = os.path.abspath(base_path)
        self.lock = threading.Lock()
        
        # Tạo thư mục gốc nếu chưa có
        if not os.path.exists(self.base_path):
            os.makedirs(self.base_path)
            print(f"[ViolationStorage] Tạo thư mục: {self.base_path}")
        
        print(f"[ViolationStorage] Initialized with base path: {self.base_path}")
    
    def save_violation(self, username: str, violation_type: str, confidence: float, 
                       image_data: bytes, additional_info: dict = None) -> str:
        """
        Lưu screenshot vi phạm
        
        Args:
            username: Tên user vi phạm
            violation_type: Loại vi phạm (gambling, socialmedia, etc.)
            confidence: Độ tin cậy của AI (0.0 - 1.0)
            image_data: Dữ liệu ảnh JPEG
            additional_info: Thông tin bổ sung (dict)
        
        Returns:
            str: Đường dẫn file đã lưu hoặc None nếu lỗi
        """
        try:
            now = datetime.now()
            year = now.strftime("%Y")
            month = now.strftime("%m")
            timestamp = now.strftime("%Y%m%d_%H%M%S_%f")[:-3]  # Bỏ 3 số cuối của microsecond
            
            # Chuẩn hóa violation type (loại bỏ emoji và ký tự đặc biệt)
            safe_violation_type = self._sanitize_filename(violation_type)
            
            # Tạo đường dẫn thư mục
            dir_path = os.path.join(
                self.base_path,
                username,
                year,
                month,
                safe_violation_type
            )
            
            with self.lock:
                if not os.path.exists(dir_path):
                    os.makedirs(dir_path)
            
            # Lưu ảnh
            image_filename = f"{timestamp}.jpg"
            image_path = os.path.join(dir_path, image_filename)
            
            with open(image_path, 'wb') as f:
                f.write(image_data)
            
            # Lưu metadata
            metadata = {
                "username": username,
                "violation_type": violation_type,
                "confidence": confidence,
                "timestamp": now.isoformat(),
                "image_size_bytes": len(image_data),
                "image_filename": image_filename
            }
            if additional_info:
                metadata.update(additional_info)
            
            metadata_filename = f"{timestamp}.json"
            metadata_path = os.path.join(dir_path, metadata_filename)
            
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            print(f"[ViolationStorage] ✅ Saved violation: {username}/{safe_violation_type}/{image_filename}")
            return image_path
            
        except Exception as e:
            print(f"[ViolationStorage] ❌ Error saving violation: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _sanitize_filename(self, name: str) -> str:
        """Loại bỏ các ký tự không hợp lệ trong tên file/folder"""
        # Loại bỏ emoji và ký tự đặc biệt
        safe_chars = []
        for c in name:
            if c.isalnum() or c in ('-', '_', '.'):
                safe_chars.append(c)
            elif c == ' ':
                safe_chars.append('_')
        
        result = ''.join(safe_chars)
        return result if result else 'unknown'
    
    def get_violations_for_user(self, username: str, limit: int = 50) -> list:
        """
        Lấy danh sách violations gần đây của một user
        
        Args:
            username: Tên user
            limit: Số lượng tối đa
        
        Returns:
            list: Danh sách metadata dict
        """
        violations = []
        user_path = os.path.join(self.base_path, username)
        
        if not os.path.exists(user_path):
            return violations
        
        try:
            # Duyệt qua các thư mục year/month/type
            for year in sorted(os.listdir(user_path), reverse=True):
                year_path = os.path.join(user_path, year)
                if not os.path.isdir(year_path):
                    continue
                    
                for month in sorted(os.listdir(year_path), reverse=True):
                    month_path = os.path.join(year_path, month)
                    if not os.path.isdir(month_path):
                        continue
                    
                    for vtype in os.listdir(month_path):
                        type_path = os.path.join(month_path, vtype)
                        if not os.path.isdir(type_path):
                            continue
                        
                        # Tìm các file .json
                        for fname in sorted(os.listdir(type_path), reverse=True):
                            if fname.endswith('.json'):
                                json_path = os.path.join(type_path, fname)
                                try:
                                    with open(json_path, 'r', encoding='utf-8') as f:
                                        metadata = json.load(f)
                                        metadata['image_path'] = os.path.join(
                                            type_path, 
                                            metadata.get('image_filename', fname.replace('.json', '.jpg'))
                                        )
                                        violations.append(metadata)
                                except:
                                    pass
                                
                                if len(violations) >= limit:
                                    return violations
        except Exception as e:
            print(f"[ViolationStorage] Error reading violations: {e}")
        
        return violations
    
    def get_recent_violations(self, limit: int = 100) -> list:
        """Lấy tất cả violations gần đây từ mọi user"""
        all_violations = []
        
        if not os.path.exists(self.base_path):
            return all_violations
        
        for username in os.listdir(self.base_path):
            user_path = os.path.join(self.base_path, username)
            if os.path.isdir(user_path):
                violations = self.get_violations_for_user(username, limit=limit)
                all_violations.extend(violations)
        
        # Sắp xếp theo thời gian giảm dần
        all_violations.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return all_violations[:limit]


# ============================================================================
# TEST
# ============================================================================
if __name__ == "__main__":
    storage = ViolationStorage("test_violations")
    
    # Test save violation
    test_image = b'\xff\xd8\xff\xe0' + b'\x00' * 100  # Fake JPEG header
    
    path = storage.save_violation(
        username="test_user",
        violation_type="🎰 Trang Cờ Bạc",
        confidence=0.95,
        image_data=test_image,
        additional_info={"ai_model": "yolov8n-cls"}
    )
    
    print(f"Saved to: {path}")
    
    # Test get violations
    violations = storage.get_violations_for_user("test_user")
    print(f"Found {len(violations)} violations")
    for v in violations:
        print(f"  - {v['violation_type']} at {v['timestamp']}")
