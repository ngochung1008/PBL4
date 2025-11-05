# # server.py

# import socket
# import threading
# import struct
# import io
# import sys
# import time
# import json
# import struct
# from PIL import Image
# from server_screen import ServerScreen  
# import config
# from remote_desktop_server import RemoteDesktopServer

# if __name__ == "__main__":
#     import signal

#     # Khởi tạo Server
#     server = RemoteDesktopServer(host="0.0.0.0") # Lắng nghe trên tất cả interfaces
    
#     def signal_handler(sig, frame):
#         print('\n[SERVER] Shutdown signal received. Starting graceful shutdown.')
#         server.close_all_connections() # Gọi phương thức đóng của lớp
#         print('[SERVER] All connections closed. Exiting now.')
#         sys.exit(0)

#     # Bắt tín hiệu Ctrl+C (SIGINT)
#     signal.signal(signal.SIGINT, signal_handler)
    
#     # Khởi động Server (bao gồm Control, Client, Transfer và Screen)
#     server.run_server()
    
#     # GIỮ LUỒNG CHÍNH CHẠY: để bắt tín hiệu Ctrl+C
#     while True:
#         time.sleep(1) 

# server.py
# -*- coding: utf-8 -*-
from __future__ import print_function
import socket
import struct
import threading
import time

TPKT_HEADER_FMT = ">BBH"

# helper to read exact n bytes
def recv_all(sock, n):
    data = b''
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            raise ConnectionError("Socket closed")
        data += chunk
    return data

class BrokerServer(object):
    def __init__(self, host="0.0.0.0", port=33890):
        self.host = host
        self.port = port
        self.server_sock = None
        self.lock = threading.Lock()
        self.clients = {}      # client_id -> socket
        self.subscribers = {}  # client_id -> [sock, ...]

    def start(self):
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_sock.bind((self.host, self.port))
        self.server_sock.listen(64)
        print("[SERVER] Listening on {}:{}".format(self.host, self.port))
        try:
            while True:
                conn, addr = self.server_sock.accept()
                t = threading.Thread(target=self.handle_conn, args=(conn, addr))
                t.daemon = True
                t.start()
        except KeyboardInterrupt:
            print("\n[SERVER] Shutting down.")
        finally:
            try:
                self.server_sock.close()
            except:
                pass

    def handle_conn(self, conn, addr):
        print("[SERVER] Connection from", addr)
        try:
            # read initial handshake (up to 128 bytes)
            conn.settimeout(5.0)
            try:
                init = conn.recv(128)
            except:
                init = b''
            conn.settimeout(None)
            if not init:
                print("[SERVER] No handshake, closing", addr)
                conn.close()
                return
            try:
                init_text = init.decode('utf-8', errors='ignore').strip()
            except:
                init_text = init.strip()

            # CLIENT:<id>
            if init_text.startswith("CLIENT:"):
                client_id = init_text.split(":",1)[1]
                print("[SERVER] Registered client id:", client_id)
                with self.lock:
                    self.clients[client_id] = conn
                    if client_id not in self.subscribers:
                        self.subscribers[client_id] = []
                # handle receiving TPKT frames and forward to subscribers
                self.handle_client_loop(client_id, conn)
            # MANAGER then SUBSCRIBE:<id>
            elif init_text.startswith("MANAGER"):
                # may have subscription on same buffer or wait for next message
                # try to read next bytes for subscribe (short)
                try:
                    sub = conn.recv(128)
                except:
                    sub = b''
                try:
                    sub_text = sub.decode('utf-8', errors='ignore').strip()
                except:
                    sub_text = sub.strip()
                if sub_text.startswith("SUBSCRIBE:"):
                    target = sub_text.split(":",1)[1]
                    print("[SERVER] Manager subscribing to", target)
                    with self.lock:
                        self.subscribers.setdefault(target, []).append(conn)
                    # keep manager connection open (do nothing else; frames will be forwarded)
                    self.handle_manager_loop(conn, target)
                else:
                    print("[SERVER] Manager connected but no subscribe. Closing.")
                    conn.close()
            else:
                print("[SERVER] Unknown handshake:", init_text[:80])
                conn.close()
        except Exception as e:
            print("[SERVER] Conn handler error:", e)
            try:
                conn.close()
            except:
                pass

    def handle_client_loop(self, client_id, conn):
        try:
            while True:
                # read TPKT
                hdr = recv_all(conn, 4)
                ver, reserved, length = struct.unpack(TPKT_HEADER_FMT, hdr)
                if ver != 0x03:
                    print("[SERVER] Bad TPKT ver from", client_id)
                    break
                payload_len = length - 4
                payload = recv_all(conn, payload_len)
                # optional: save locally or process
                print("[SERVER] Received frame from {} ({} bytes)".format(client_id, payload_len))
                # forward to subscribers
                with self.lock:
                    subs = list(self.subscribers.get(client_id, []))
                for s in subs:
                    try:
                        s.sendall(hdr + payload)
                    except Exception as e:
                        print("[SERVER] Forward to manager failed, removing subscriber:", e)
                        with self.lock:
                            try:
                                self.subscribers[client_id].remove(s)
                            except:
                                pass
        except ConnectionError:
            print("[SERVER] Client {} disconnected".format(client_id))
        except Exception as e:
            print("[SERVER] Error in client loop {}: {}".format(client_id, e))
        finally:
            with self.lock:
                try:
                    del self.clients[client_id]
                except:
                    pass
                # optionally notify subscribers
            try:
                conn.close()
            except:
                pass

    def handle_manager_loop(self, conn, client_id):
        # just hold the connection open until closed by manager
        try:
            while True:
                data = conn.recv(1)
                if not data:
                    break
        except:
            pass
        finally:
            print("[SERVER] Manager disconnected for", client_id)
            with self.lock:
                try:
                    self.subscribers[client_id].remove(conn)
                except:
                    pass
            try:
                conn.close()
            except:
                pass

if __name__ == "__main__":
    server = BrokerServer(host="0.0.0.0", port=33890)
    server.start()
