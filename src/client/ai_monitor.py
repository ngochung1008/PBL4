# client/ai_monitor.py
"""
AI Monitor Module - Giám sát màn hình client bằng AI
Sử dụng model YOLOv8 đã train để phân loại trang web:
- gambling: Trang cờ bạc (CẤM)
- socialmedia: Mạng xã hội (CẤM)
- safe: An toàn (CHO PHÉP)
"""

import threading
import time
import os
import io
from datetime import datetime
from PIL import Image

# Đường dẫn đến model đã train
MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'ai_training', 'runs', 'monitor_model', 'weights', 'best.pt')

# Danh sách các class bị CẤM
FORBIDDEN_CLASSES = ['gambling', 'socialmedia']

# Ngưỡng tin cậy để trigger alert (0.0 - 1.0)
CONFIDENCE_THRESHOLD = 0.7

# Thời gian chờ giữa các lần scan (giây)
SCAN_INTERVAL = 5

class AIMonitor(threading.Thread):
    """
    Thread giám sát màn hình bằng AI
    Khi phát hiện trang web bị cấm:
    1. Gửi security alert đến server
    2. Chụp full frame và gửi kèm
    """
    
    def __init__(self, screenshot_module, send_alert_callback, send_screenshot_callback=None, logger=None):
        """
        Args:
            screenshot_module: ClientScreenshot instance để chụp màn hình
            send_alert_callback: Hàm gửi security alert (message: str)
            send_screenshot_callback: Hàm gửi screenshot violation (image_bytes: bytes, class_name: str)
            logger: Logger function
        """
        super().__init__(daemon=True, name="AIMonitor")
        self.screenshot = screenshot_module
        self.send_alert = send_alert_callback
        self.send_screenshot = send_screenshot_callback
        self.logger = logger or print
        self.running = False
        self.model = None
        self.last_alert_time = {}  # Track last alert time per class
        self.alert_cooldown = 30  # Chỉ alert mỗi 30 giây cho mỗi loại vi phạm
        
    def _load_model(self):
        """Load YOLO model"""
        try:
            from ultralytics import YOLO
            
            # Kiểm tra file model tồn tại
            model_path = os.path.abspath(MODEL_PATH)
            if not os.path.exists(model_path):
                self.logger(f"[AIMonitor] ❌ Không tìm thấy model tại: {model_path}")
                return False
                
            self.logger(f"[AIMonitor] 📦 Đang load model từ: {model_path}")
            self.model = YOLO(model_path)
            self.logger(f"[AIMonitor] ✅ Model loaded thành công!")
            
            # Log các class có thể detect
            if hasattr(self.model, 'names'):
                self.logger(f"[AIMonitor] 📋 Classes: {self.model.names}")
            
            return True
        except ImportError:
            self.logger("[AIMonitor] ❌ Chưa cài ultralytics. Chạy: pip install ultralytics")
            return False
        except Exception as e:
            self.logger(f"[AIMonitor] ❌ Lỗi load model: {e}")
            return False
    
    def _analyze_screen(self, img):
        """
        Phân tích ảnh màn hình bằng AI
        
        Args:
            img: PIL Image
            
        Returns:
            tuple: (class_name, confidence) hoặc (None, 0) nếu không phát hiện vi phạm
        """
        if self.model is None:
            return None, 0
            
        try:
            # Chuyển sang RGB nếu cần
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Predict
            results = self.model.predict(img, imgsz=224, verbose=False)
            
            if results and len(results) > 0:
                result = results[0]
                
                # Lấy class có xác suất cao nhất
                probs = result.probs
                if probs is not None:
                    top1_idx = probs.top1
                    top1_conf = probs.top1conf.item()
                    class_name = self.model.names[top1_idx]
                    
                    return class_name, top1_conf
                    
        except Exception as e:
            self.logger(f"[AIMonitor] ⚠️ Lỗi analyze: {e}")
            
        return None, 0
    
    def _should_alert(self, class_name):
        """Kiểm tra xem có nên gửi alert không (tránh spam)"""
        now = time.time()
        last_time = self.last_alert_time.get(class_name, 0)
        
        if now - last_time >= self.alert_cooldown:
            self.last_alert_time[class_name] = now
            return True
        return False
    
    def _capture_violation_screenshot(self, img, class_name, confidence):
        """
        Chụp screenshot vi phạm và gửi đến server
        
        Args:
            img: PIL Image
            class_name: Loại vi phạm
            confidence: Độ tin cậy
        """
        try:
            # Encode ảnh thành JPEG với chất lượng cao
            buffer = io.BytesIO()
            if img.mode != 'RGB':
                img = img.convert('RGB')
            img.save(buffer, format='JPEG', quality=90)
            image_bytes = buffer.getvalue()
            
            # Gửi screenshot nếu có callback
            if self.send_screenshot:
                self.send_screenshot(image_bytes, class_name, confidence)
                self.logger(f"[AIMonitor] 📸 Đã gửi screenshot vi phạm: {class_name}")
            
            return image_bytes
        except Exception as e:
            self.logger(f"[AIMonitor] ❌ Lỗi capture screenshot: {e}")
            return None
    
    def run(self):
        """Main loop - quét màn hình định kỳ"""
        self.running = True
        
        # Load model trước khi bắt đầu
        if not self._load_model():
            self.logger("[AIMonitor] ⛔ Không thể khởi động do lỗi load model")
            return
            
        self.logger(f"[AIMonitor] 🚀 Bắt đầu giám sát (scan mỗi {SCAN_INTERVAL}s)")
        
        while self.running:
            try:
                # 1. Chụp màn hình
                img = self.screenshot.capture_once()
                
                # 2. Phân tích bằng AI
                class_name, confidence = self._analyze_screen(img)
                
                # 3. Kiểm tra vi phạm
                if class_name and class_name in FORBIDDEN_CLASSES:
                    if confidence >= CONFIDENCE_THRESHOLD:
                        self.logger(f"[AIMonitor] 🚨 PHÁT HIỆN VI PHẠM: {class_name} ({confidence*100:.1f}%)")
                        
                        # Chỉ gửi alert nếu chưa gửi gần đây
                        if self._should_alert(class_name):
                            # Tạo message alert
                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            violation_type = self._get_violation_type_name(class_name)
                            detail = f"AI phát hiện: {class_name} (độ tin cậy: {confidence*100:.1f}%) lúc {timestamp}"
                            
                            # Gửi security alert
                            alert_msg = f"security_alert:{violation_type}|{detail}"
                            self.send_alert(alert_msg)
                            
                            # Chụp và gửi screenshot vi phạm
                            self._capture_violation_screenshot(img, class_name, confidence)
                            
                            self.logger(f"[AIMonitor] ✅ Đã gửi cảnh báo: {violation_type}")
                    else:
                        # Debug log cho trường hợp confidence thấp
                        self.logger(f"[AIMonitor] 📊 Detect: {class_name} ({confidence*100:.1f}%) - dưới ngưỡng {CONFIDENCE_THRESHOLD*100:.0f}%")
                else:
                    # Debug log định kỳ
                    if class_name:
                        pass  # Có thể log nếu muốn: self.logger(f"[AIMonitor] ✓ Screen: {class_name} ({confidence*100:.1f}%)")
                
                # 4. Chờ trước khi scan tiếp
                time.sleep(SCAN_INTERVAL)
                
            except Exception as e:
                self.logger(f"[AIMonitor] ❌ Lỗi trong vòng lặp: {e}")
                time.sleep(SCAN_INTERVAL)
                
        self.logger("[AIMonitor] 🛑 Đã dừng giám sát")
    
    def _get_violation_type_name(self, class_name):
        """Chuyển class name thành tên violation dễ đọc"""
        mapping = {
            'gambling': '🎰 Trang Cờ Bạc',
            'socialmedia': '📱 Mạng Xã Hội',
        }
        return mapping.get(class_name, f'⚠️ Vi phạm: {class_name}')
    
    def stop(self):
        """Dừng monitor"""
        self.running = False
        self.logger("[AIMonitor] Đang dừng...")


# ============================================================================
# TEST
# ============================================================================
if __name__ == "__main__":
    print("Testing AIMonitor...")
    
    # Mock screenshot module
    class MockScreenshot:
        def capture_once(self):
            # Tạo ảnh test
            return Image.new('RGB', (224, 224), color='red')
    
    def mock_alert(msg):
        print(f"ALERT: {msg}")
    
    def mock_screenshot(img_bytes, class_name, conf):
        print(f"SCREENSHOT: {class_name} ({conf*100:.1f}%), size={len(img_bytes)} bytes")
    
    monitor = AIMonitor(
        MockScreenshot(), 
        mock_alert, 
        mock_screenshot,
        print
    )
    
    # Test load model
    if monitor._load_model():
        print("Model loaded!")
        
        # Test analyze với ảnh random
        img = Image.new('RGB', (224, 224), color='blue')
        class_name, conf = monitor._analyze_screen(img)
        print(f"Analyze result: {class_name} ({conf*100:.1f}%)")
