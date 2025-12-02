# server0/server_logger.py
import datetime
import os

class ServerLogger:
    LOG_FILE = "security_alerts.log"

    @staticmethod
    def log_alert(client_id, violation_type, detail):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] CLIENT: {client_id} | TYPE: {violation_type} | MSG: {detail}\n"
        
        # Ghi vào file (hoặc DB sau này)
        try:
            with open(ServerLogger.LOG_FILE, "a", encoding="utf-8") as f:
                f.write(log_entry)
            print(f"[LOGGER] Đã ghi cảnh báo: {log_entry.strip()}")
        except Exception as e:
            print(f"[LOGGER] Lỗi ghi log: {e}")