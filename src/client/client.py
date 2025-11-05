from __future__ import print_function
from client_screen import ClientScreenSender

if __name__ == "__main__":
    SERVER_HOST = "10.10.58.163"
    SERVER_PORT = 33890
    CLIENT_ID = "client01"

    sender = ClientScreenSender(SERVER_HOST, SERVER_PORT, CLIENT_ID, fps=2, quality=75, max_dimension=1280)
    try:
        sender.run()
    except KeyboardInterrupt:
        print("\n[CLIENT] stopped by user")
