# manager.py

import threading
import socket
import sys
import json
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QCursor
from PyQt6.QtCore import QThread
import time
from manager_input import ManagerInput
from manager_viewer import ManagerViewer
from transfer_channel import TransferChannel
# Ghi chú: Thư viện socket đã được sử dụng đúng cách
# Ghi chú: Sử dụng QThread để xử lý event loop của UI (app.exec())
import config

SERVER_HOST = config.SERVER_HOST
CONTROL_PORT = config.CONTROL_PORT
SCREEN_PORT = config.SCREEN_PORT
TRANSFER_PORT = config.TRANSFER_PORT

# Hàm này xử lý các gói JSON (chủ yếu là cursor_update) được Server forward từ Client.
def start_recv_loop(sock, viewer):
    buffer = b""
    try:
        while True:
            data = sock.recv(4096)
            if not data:
                break
            buffer += data
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                try:
                    ev = json.loads(line.decode("utf-8"))
                    if ev.get("device") == "mouse" and ev.get("type") == "cursor_update":
                        # Quyết định có cho phép Client điều khiển con trỏ Manager hay không
                        # Chỉ cho phép Client điều khiển nếu Manager KHÔNG đang điều khiển Client (chuột đang ở ngoài cửa sổ)
                        move_allowed = not (viewer.input_handler and viewer.input_handler.is_controlling)
                        # Hiển thị chấm đỏ và di chuyển con trỏ hệ thống (move_system_cursor=True)
                        viewer.show_remote_cursor(int(ev["x"]), int(ev["y"]), move_system_cursor=move_allowed)
                    # có thể xử lý thêm event khác nếu cần
                except Exception as e:
                    print("[MANAGER] Parse error:", e)
    except Exception as e:
        print("[MANAGER] Receive loop error:", e)
    
    """ Khi luồng nhận (từ Server) bị ngắt (do Server/Client đóng), 
    hiển thị thông báo và đóng cửa sổ ManagerViewer."""
    print("[MANAGER] Receiver loop ended. Closing viewer.")
    viewer.on_connection_lost("Kết nối input/server bị mất.")
    viewer.close() # Đóng cửa sổ (sẽ kích hoạt closeEvent)

if __name__ == "__main__":
    # Khởi tạo QApplication 
    app = QApplication(sys.argv)

    # Khởi tạo Viewer (nhận màn hình)
    viewer = ManagerViewer(SERVER_HOST, SCREEN_PORT)

    # Xử lý kết nối Input/Cursor
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((SERVER_HOST, CONTROL_PORT))
        print("[MANAGER] Connected to server for input")
    except Exception as e:
        print(f"[MANAGER] Could not connect to input server: {e}")
        sys.exit(1) # Thoát nếu không kết nối được

    viewer.show()  # Hiển thị cửa sổ viewer

    # Input handler (gửi sự kiện bàn phím/chuột)
    input_handler = ManagerInput(sock, viewer=viewer)

    # Lưu sock input vào viewer để có thể đóng khi cửa sổ viewer đóng
    viewer.input_socket = sock

    # Gắn input handler vào viewer để viewer có thể tạm vô hiệu hoá
    viewer.set_input_handler(input_handler)

    # 1. Định nghĩa callback để xử lý gói nhận
    def handle_transfer_package(pkg):
        pkg_type = pkg.get("type")
        sender = pkg.get("sender")
        data = pkg.get("data")
        
        if pkg_type == "chat":
            print(f"[CHAT] {sender}: {data}")
            # Cập nhật UI chatbox
        elif pkg_type == "file_meta":
            # Bắt đầu chuẩn bị nhận file (tên file, kích thước)
            print(f"[FILE] Nhận thông tin file từ {sender}: {data['filename']}")
            # Kích hoạt luồng/lớp nhận file

    # 2. Khởi tạo và kết nối TransferChannel
    transfer_channel = TransferChannel(SERVER_HOST, TRANSFER_PORT, handle_transfer_package)
    if not transfer_channel.connect():
        print("[MANAGER] Could not connect to transfer server.")
        # Xử lý lỗi nếu cần

    # Chờ frame đầu tiên để có thể map tọa độ (đảm bảo remote_width có giá trị)
    waited = 0.0
    while waited < 5.0:
        app.processEvents()
        if getattr(viewer, "remote_width", 0) and viewer.remote_width > 1:
            break
        time.sleep(0.05)
        waited += 0.05

    # Gửi initial set_position sync để đồng bộ con trỏ Client với Manager
    mapped = viewer.get_current_mapped_remote()
    if mapped:
        try:
            sync_event = {"device": "mouse", "type": "set_position", "x": mapped[0], "y": mapped[1]}
            sock.sendall((json.dumps(sync_event) + "\n").encode("utf-8"))
            print("[MANAGER] Sent initial set_position sync.")
        except Exception as e:
            print("[MANAGER] Sync send error:", e)
    
    # Bắt đầu luồng nhận các sự kiện Client (cursor_update)
    threading.Thread(target=start_recv_loop, args=(sock, viewer), daemon=True).start()

    # Khởi listener cho input (pynput)
    threading.Thread(target=input_handler.run, daemon=True).start() 

    # Chạy vòng lặp chính của UI
    sys.exit(app.exec())