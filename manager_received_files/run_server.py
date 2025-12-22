"""
Server Launcher - Khởi động tất cả servers
Chạy: python run_server.py
"""
import sys
import os
import threading

sys.path.insert(0, os.getcwd())

def run_auth_server():
    """Chạy Auth Server (port 5001)"""
    try:
        from src.server.core.auth_server import start_server
        print("[Auth Server] Dang khoi dong tren port 5001...")
        start_server()
    except Exception as e:
        print(f'[Auth Server] Error: {e}')

def run_main_server():
    """Chạy Main Server (port 5000)"""
    try:
        from src.server.server import main
        print("[Main Server] Dang khoi dong tren port 5000...")
        main()
    except Exception as e:
        print(f'[Main Server] Error: {e}')

if __name__ == "__main__":
    print("="*60)
    print("KHOI DONG TAT CA SERVERS")
    print("="*60)
    print()
    
    import time
    
    # Chạy Auth Server trong thread riêng
    auth_thread = threading.Thread(target=run_auth_server, daemon=True)
    auth_thread.start()
    
    # Đợi Auth Server khởi động xong
    print("Doi Auth Server khoi dong...")
    time.sleep(2)
    
    # Chạy Main Server trong main thread
    try:
        run_main_server()
    except KeyboardInterrupt:
        print("\n\nDang dung servers...")
        print("Da dung.")