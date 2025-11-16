# manager.py
import argparse
from client.manager.manager_network.manager_app import ManagerApp

def main():
    parser = argparse.ArgumentParser(description="Manager – xem & điều khiển client qua server.")
    parser.add_argument("server_host", help="Địa chỉ IP của server")
    parser.add_argument("server_port", type=int, help="Cổng của server")
    parser.add_argument("--id", default="manager1", help="ID của manager")
    args = parser.parse_args()

    app = ManagerApp(server_host=args.server_host, server_port=args.server_port, manager_id=args.id)
    app.start()

if __name__ == "__main__":
    main()
