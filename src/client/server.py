# server.py

import socket
import threading
import struct
import io
import sys
import time
import json
import struct
from PIL import Image
from server_screen import ServerScreen  
import config
from remote_desktop_server import RemoteDesktopServer

if __name__ == "__main__":
    import signal

    # Khởi tạo Server
    server = RemoteDesktopServer(host="0.0.0.0") # Lắng nghe trên tất cả interfaces
    
    def signal_handler(sig, frame):
        print('\n[SERVER] Shutdown signal received. Starting graceful shutdown.')
        server.close_all_connections() # Gọi phương thức đóng của lớp
        sys.exit(0)

    # Bắt tín hiệu Ctrl+C (SIGINT)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Khởi động Server (bao gồm Control, Client, Transfer và Screen)
    server.run_server()
    
    # GIỮ LUỒNG CHÍNH CHẠY: để bắt tín hiệu Ctrl+C
    while True:
        time.sleep(1)