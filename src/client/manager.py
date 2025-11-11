# manager.py
from manager_viewer import ManagerViewer
from manager_sender import ManagerSender
from manager_input import ManagerInput
import threading

SERVER_HOST = "10.227.28.77"
SERVER_PORT = 33900

def main():
    sender = ManagerSender(SERVER_HOST, SERVER_PORT)
    sender.connect()

    viewer = ManagerViewer(SERVER_HOST, SERVER_PORT)
    input_ctrl = ManagerInput(sender, viewer)
    threading.Thread(target=input_ctrl.run, daemon=True).start()

    viewer.start()

if __name__ == "__main__":
    main()
