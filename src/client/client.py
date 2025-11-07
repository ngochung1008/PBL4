# client.py
# -*- coding: utf-8 -*-
from client_screenshot import ClientScreenshot
from client_screen_sender import ClientScreenSender
import threading
import signal
import sys

def main():
    SERVER_HOST = "10.10.30.88"
    SERVER_PORT = 33890
    CLIENT_ID = "client01"

    # config
    fps = 2
    quality = 75
    max_dimension = 1280
    use_encryption = False   # set True nếu đã cài PyCryptodome và muốn mã hóa
    rect_threshold_area = 20000  # px^2

    capturer = ClientScreenshot(fps=fps, quality=quality, max_dimension=max_dimension, detect_delta=True)
    sender = ClientScreenSender(SERVER_HOST, SERVER_PORT, CLIENT_ID,
                            use_encryption=use_encryption,
                            rect_threshold_area=rect_threshold_area)


    # start sender thread
    t_sender = threading.Thread(target=sender.send_loop, daemon=True)
    t_sender.start()

    # start capturer (runs in main thread)
    def shutdown(signum, frame):
        print("\n[MAIN] shutting down...")
        capturer.stop = True
        sender.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        capturer.capture_loop(sender.enqueue_frame)
    except KeyboardInterrupt:
        shutdown(None, None)


if __name__ == "__main__":
    main()
