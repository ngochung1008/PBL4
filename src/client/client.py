# client.py
import argparse
from client.client_network.client_network import ClientNetwork
from client.client_network.client_sender import ClientSender
from client.client_screenshot import ClientScreenshot
from client.client_input import ClientInputHandler

def main():
    parser = argparse.ArgumentParser(description="Client – gửi màn hình & nhận điều khiển từ server.")
    parser.add_argument("server_host", help="Địa chỉ IP của server")
    parser.add_argument("server_port", type=int, help="Cổng của server")
    parser.add_argument("--id", default="client1", help="ID của client")
    args = parser.parse_args()

    client_net = ClientNetwork(args.server_host, args.server_port, client_id=args.id)
    if not client_net.connect():
        print("❌ Kết nối thất bại.")
        return

    sender = ClientSender(client_net.sock)
    sender.start()

    capturer = ClientScreenshot(fps=2)
    try:
        capturer.capture_loop(lambda w,h,jpg,bbox,img,seq,ts: sender.enqueue_frame(w,h,jpg,bbox,seq,ts))
    except KeyboardInterrupt:
        capturer.stop = True
        sender.stop()

if __name__ == "__main__":
    main()
