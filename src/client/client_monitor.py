# client/client_monitor.py (Gợi ý code Client)
import threading
import time
import pygetwindow as gw # Cần pip install pygetwindow
# import ... (thư viện AI của bạn, ví dụ ultralytics YOLO)

class ClientMonitor(threading.Thread):
    def __init__(self, client_network_callback):
        super().__init__(daemon=True)
        self.callback = client_network_callback # Hàm gửi PDU của ClientNetwork
        self.running = True

    def run(self):
        while self.running:
            try:
                # --- CÁCH 1: KIỂM TRA TIÊU ĐỀ CỬA SỔ (Nhẹ, Nhanh) ---
                active_window = gw.getActiveWindow()
                if active_window:
                    title = active_window.title.lower()
                    bad_keywords = ["bet88", "nhà cái", "phimmoi", "xoilac"]
                    
                    for kw in bad_keywords:
                        if kw in title:
                            self.trigger_alert("Web Cấm", f"Đang truy cập: {title}")
                            # Có thể thêm lệnh đóng cửa sổ: active_window.close()
                
                # --- CÁCH 2: DÙNG AI (Nặng hơn) ---
                # img = chụp_màn_hình()
                # result = model_ai.predict(img)
                # if result == "football":
                #     self.trigger_alert("Giải trí", "Đang xem bóng đá")

                time.sleep(5) # Kiểm tra mỗi 5 giây
            except Exception as e:
                print(f"Lỗi monitor: {e}")

    def trigger_alert(self, type_name, detail):
        # Gửi lệnh lên server
        msg = f"security_alert:{type_name}|{detail}"
        self.callback(msg) # Gọi hàm send_control_pdu của ClientNetwork