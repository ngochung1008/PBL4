# manager.py
from manager_viewer import ManagerViewer
from manager_sender import ManagerSender
import threading, time

SERVER_HOST = "10.10.30.88"
MANAGER_ID = "manager1"
TARGET_CLIENT_ID = "client01"  # which client to control

def main():
    sender = ManagerSender(SERVER_HOST, 33900, manager_id=MANAGER_ID)
    sender.connect()
    viewer = ManagerViewer(SERVER_HOST, 33900, manager_id=MANAGER_ID, on_click=lambda action,x,y,e: on_input(action,x,y,e, viewer, sender))
    # run viewer in main thread
    threading.Thread(target=viewer.connect, daemon=True).start()
    viewer.start_mainloop()

def on_input(action, x, y, event, viewer, sender):
    """
    Convert canvas coords to client's screen coords.
    Here we assume manager displayed the full frame (or same aspect).
    If viewer.full_size is known, scale accordingly.
    """
    try:
        full_w, full_h = viewer.full_size
        canvas_w = viewer.canvas.winfo_width() or 1
        canvas_h = viewer.canvas.winfo_height() or 1
        if full_w and full_h:
            sx = int(x * (full_w / canvas_w))
            sy = int(y * (full_h / canvas_h))
        else:
            sx, sy = x, y
        if action == "move":
            inp = {"client_id": TARGET_CLIENT_ID, "type":"mouse","action":"move","x":sx,"y":sy}
            sender.send_input(inp)
        elif action == "click":
            inp = {"client_id": TARGET_CLIENT_ID, "type":"mouse","action":"click","x":sx,"y":sy,"button":"left"}
            sender.send_input(inp)
        elif action == "down":
            inp = {"client_id": TARGET_CLIENT_ID, "type":"mouse","action":"down","x":sx,"y":sy,"button":"left"}
            sender.send_input(inp)
        elif action == "up":
            inp = {"client_id": TARGET_CLIENT_ID, "type":"mouse","action":"up","x":sx,"y":sy,"button":"left"}
            sender.send_input(inp)
    except Exception as e:
        print("[MANAGER] on_input error:", e)

if __name__ == "__main__":
    main()
