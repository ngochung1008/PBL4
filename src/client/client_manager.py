import socket

SERVER_HOST = "10.10.30.179"   # IP server
CONTROL_PORT = 9010

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((SERVER_HOST, CONTROL_PORT))
        print("[MANAGER] Connected to server")
        while True:
            cmd = input("Enter command> ")
            if cmd.strip().lower() == "exit":
                break
            s.sendall(cmd.encode("utf-8"))

if __name__ == "__main__":
    main()