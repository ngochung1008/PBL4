# manager.py

import threading
import socket
import sys
import json
from PyQt6.QtWidgets import QApplication
from manager_input import ManagerInput
from manager_viewer import ManagerViewer

SERVER_HOST = "10.248.230.77"
CONTROL_PORT = 9010   # gửi input tới server
SCREEN_PORT = 5000    # nhận màn hình từ server

def start_recv_loop(sock, viewer):
    """Nhận các event từ client (qua server) và cập nhật viewer (ví dụ cursor_update)."""
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
                        # client đang gửi vị trí thật -> hiển thị trên viewer
                        viewer.show_remote_cursor(int(ev["x"]), int(ev["y"]))
                    # có thể xử lý thêm event khác nếu cần
                except Exception as e:
                    print("[MANAGER] Parse error:", e)
    except Exception as e:
        print("[MANAGER] Receive loop error:", e)
    print("[MANAGER] Receiver loop ended.")

if __name__ == "__main__":
    # Khởi tạo QApplication trước
    app = QApplication(sys.argv)

    # Viewer handler (nhận màn hình từ server) - tạo trước để truyền vào input handler
    viewer = ManagerViewer(SERVER_HOST, SCREEN_PORT)
    viewer.show()

    # Kết nối tới server để gửi input
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((SERVER_HOST, CONTROL_PORT))
    print("[MANAGER] Connected to server for input")

    # Input handler (gửi sự kiện bàn phím/chuột) - truyền viewer để dùng scale nếu cần
    input_handler = ManagerInput(sock, viewer=viewer)

    # Gắn input handler vào viewer để viewer có thể tạm vô hiệu hoá khi đặt con trỏ hệ thống
    viewer.set_input_handler(input_handler)

    # Chờ frame đầu tiên để có thể map tọa độ
    while not viewer.remote_width > 1:
        app.processEvents()
        time.sleep(0.1)

    # Lấy vị trí chuột hiện tại của manager
    current_pos = QCursor.pos()
    label_pos = viewer.label.mapFromGlobal(current_pos)
    
    # Map sang tọa độ remote
    if label_pos:
        mapped = viewer.label_coords_to_remote(label_pos.x(), label_pos.y())
        if mapped:
            # Gửi sync event với vị trí chuột của manager
            sync_event = {
                "device": "mouse",
                "type": "set_position",
                "x": mapped[0],
                "y": mapped[1]
            }
            sock.sendall((json.dumps(sync_event) + "\n").encode())

    # Start receiver thread to get client -> manager forwarded events
    threading.Thread(target=start_recv_loop, args=(sock, viewer), daemon=True).start()

    # Khởi listener cho input (trong thread)
    threading.Thread(target=input_handler.run, daemon=True).start()

    # Wait until viewer received at least one frame (để mapping khả dụng) - tối đa 5s
    import time
    waited = 0.0
    while waited < 5.0:
        app.processEvents()
        if getattr(viewer, "remote_width", 0) and viewer.remote_width > 1:
            break
        time.sleep(0.05)
        waited += 0.05

    # Send initial sync: lấy vị trí hiện tại trên viewer (nếu nằm trong vùng hiển thị)
    mapped = viewer.get_current_mapped_remote()
    if mapped:
        try:
            sync_event = {"device": "mouse", "type": "set_position", "x": mapped[0], "y": mapped[1]}
            sock.sendall((json.dumps(sync_event) + "\n").encode("utf-8"))
            print("[MANAGER] Sent initial set_position sync:", sync_event)
        except Exception as e:
            print("[MANAGER] Sync send error:", e)

    sys.exit(app.exec())