from __future__ import print_function
from manager_screen import ManagerScreenReceiver

if __name__ == "__main__":
    SERVER_HOST = "10.10.58.163"
    SERVER_PORT = 33890
    TARGET_CLIENT_ID = "client01"

    mgr = ManagerScreenReceiver(SERVER_HOST, SERVER_PORT, TARGET_CLIENT_ID)
    try:
        mgr.run()
    except KeyboardInterrupt:
        print("\n[MANAGER] stopped by user")
