# server_control.py
import socket

HOST = "0.0.0.0"
PORT = 9010

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen(1)
        print(f"Server listening on {HOST}:{PORT}")
        conn, addr = s.accept()
        with conn:
            print("Connected by", addr)
            while True:
                cmd = input("Enter command> ")  # ví dụ: MOVE 100 200 / CLICK / TYPE hello
                if cmd.strip().lower() == "exit":
                    break
                conn.sendall(cmd.encode("utf-8"))

if __name__ == "__main__":
    main()