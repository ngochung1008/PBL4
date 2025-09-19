# server_relay.py
import socket
import threading

MANAGER_PORT = 9010
CLIENT_PORT = 9011

clients = {}  # lưu danh sách client {addr: conn}

def handle_manager(conn, addr):
    print("Manager connected:", addr)
    try:
        while True:
            cmd = conn.recv(1024).decode("utf-8")
            if not cmd:
                break
            print(f"[Manager] {cmd}")
            # gửi cho tất cả client (hoặc chọn client theo ID)
            for caddr, cconn in clients.items():
                try:
                    cconn.sendall(cmd.encode("utf-8"))
                    print(f"Sent to client {caddr}")
                except:
                    pass
    finally:
        conn.close()

def handle_client(conn, addr):
    print("Client connected:", addr)
    clients[addr] = conn
    try:
        while True:
            data = conn.recv(1024)
            if not data:
                break
            print(f"[Client {addr}] {data.decode('utf-8')}")
    finally:
        del clients[addr]
        conn.close()

def start_server():
    # socket manager
    sm = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sm.bind(("0.0.0.0", MANAGER_PORT))
    sm.listen(1)
    print(f"Listening for manager on port {MANAGER_PORT}")

    # socket client
    sc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sc.bind(("0.0.0.0", CLIENT_PORT))
    sc.listen(5)
    print(f"Listening for clients on port {CLIENT_PORT}")

    threading.Thread(target=accept_loop, args=(sm, handle_manager)).start()
    threading.Thread(target=accept_loop, args=(sc, handle_client)).start()

def accept_loop(sock, handler):
    while True:
        conn, addr = sock.accept()
        threading.Thread(target=handler, args=(conn, addr)).start()

if __name__ == "__main__":
    start_server()