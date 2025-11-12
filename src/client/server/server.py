# server.py
import argparse
from client.server.server_network.server_app import ServerApp

def main():
    # Khởi động server trung gian (nhận kết nối từ client & manager)
    app = ServerApp(host="0.0.0.0", port=9000)
    print(f"🚀 Server đang chạy tại {app.host}:{app.port}")
    app.start()

if __name__ == "__main__":
    main()
