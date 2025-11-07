# client.py
from client_screenshot import ClientScreenshot
from client_sender import ClientScreenSender
import threading, signal, sys

def main():
    SERVER_HOST = "10.10.30.88"
    SERVER_PORT = 33890
    CLIENT_ID = "client01"

    capturer = ClientScreenshot(fps=2, quality=75, max_dimension=1280, detect_delta=True)
    sender = ClientScreenSender(SERVER_HOST, SERVER_PORT, CLIENT_ID, rect_threshold_area=20000)
    sender.start()

    def shutdown(signum, frame):
        print("[MAIN] shutting down")
        capturer.stop = True
        sender.stop()
        sys.exit(0)

    import signal
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        capturer.capture_loop(sender.enqueue_frame)
    except KeyboardInterrupt:
        shutdown(None, None)

if __name__ == "__main__":
    main()
