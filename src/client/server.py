# server.py
import socket
import threading
import time
from common_network.x224_handshake import X224Handshake
from common_network.tpkt_layer import TPKTLayer
from common_network.pdu_parser import PDUParser

CLIENT_PORT = 33890
MANAGER_PORT = 33900

# Keep track of clients and managers as dict: id -> conn
clients = {}
clients_lock = threading.Lock()

managers = set()
managers_lock = threading.Lock()

parser = PDUParser()

def forward_to_managers(tpkt_bytes):
    with managers_lock:
        dead = []
        for m in list(managers):
            try:
                m.sendall(tpkt_bytes)
            except Exception:
                dead.append(m)
        for d in dead:
            managers.discard(d)
            try: d.close()
            except: pass

def send_to_client_by_id(client_id, tpkt_bytes):
    with clients_lock:
        conn = clients.get(client_id)
        if not conn:
            return False
        try:
            conn.sendall(tpkt_bytes)
            return True
        except Exception:
            try: conn.close()
            except: pass
            del clients[client_id]
            return False

class ClientHandler(threading.Thread):
    def __init__(self, conn, addr):
        super().__init__(daemon=True)
        self.conn = conn
        self.addr = addr
        self.client_id = None

    def run(self):
        try:
            ok, client_id = X224Handshake.server_do_handshake(self.conn)
            if not ok:
                print(f"[SERVER] client handshake failed {self.addr}")
                self.conn.close()
                return
            self.client_id = client_id
            print(f"[SERVER] client connected id={self.client_id} addr={self.addr}")
            with clients_lock:
                clients[self.client_id] = self.conn

            while True:
                hdr = X224Handshake.recv_all(self.conn, 4)
                ver, rsv, length = TPKTLayer.unpack_header(hdr)
                body = X224Handshake.recv_all(self.conn, length - 4)
                full = hdr + body
                # parse for logging
                try:
                    pdu = parser.parse(body)
                    if pdu['type'] in ('full','rect'):
                        # forward screen updates to all managers
                        forward_to_managers(full)
                    elif pdu['type'] == 'control':
                        print(f"[SERVER] control from client {self.client_id}: {pdu.get('message')}")
                    elif pdu['type'] == 'input':
                        # client should not send input normally, ignore/log
                        pass
                except Exception:
                    # forward by default
                    forward_to_managers(full)
        except Exception as e:
            print("[SERVER] client handler error:", e)
        finally:
            print(f"[SERVER] client disconnected {self.addr}")
            with clients_lock:
                if self.client_id in clients:
                    try: clients[self.client_id].close()
                    except: pass
                    del clients[self.client_id]

class ManagerHandler(threading.Thread):
    def __init__(self, conn, addr):
        super().__init__(daemon=True)
        self.conn = conn
        self.addr = addr
        self.manager_id = None

    def run(self):
        try:
            ok, manager_id = X224Handshake.server_do_handshake(self.conn)
            if not ok:
                print(f"[SERVER] manager handshake failed {self.addr}")
                self.conn.close()
                return
            self.manager_id = manager_id
            print(f"[SERVER] manager connected id={self.manager_id} addr={self.addr}")
            with managers_lock:
                managers.add(self.conn)

            # receive input PDUs from manager and forward to target client
            while True:
                hdr = X224Handshake.recv_all(self.conn, 4)
                ver, rsv, length = TPKTLayer.unpack_header(hdr)
                body = X224Handshake.recv_all(self.conn, length - 4)
                pdu = parser.parse(body)
                if pdu['type'] == 'input':
                    # INPUT payload MUST include target client id (e.g., input["client_id"])
                    inp = pdu.get('input') or {}
                    target = inp.get('client_id')
                    if target:
                        # forward the original tpkt raw bytes to client
                        full = hdr + body
                        ok = send_to_client_by_id(target, full)
                        if not ok:
                            print(f"[SERVER] failed to forward input to {target}")
                else:
                    # managers normally don't send screen frames; ignore or log
                    pass
        except Exception as e:
            print("[SERVER] manager handler error:", e)
        finally:
            print(f"[SERVER] manager disconnected {self.addr}")
            with managers_lock:
                try: managers.discard(self.conn)
                except: pass
            try: self.conn.close()
            except: pass

def start_server(host=''):
    # manager acceptor
    def accept_managers():
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((host, MANAGER_PORT))
        sock.listen(10)
        print(f"[SERVER] manager listen on {host}:{MANAGER_PORT}")
        while True:
            conn, addr = sock.accept()
            ManagerHandler(conn, addr).start()

    threading.Thread(target=accept_managers, daemon=True).start()

    # client acceptor (main thread)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((host, CLIENT_PORT))
    sock.listen(10)
    print(f"[SERVER] client listen on {host}:{CLIENT_PORT}")
    try:
        while True:
            conn, addr = sock.accept()
            ClientHandler(conn, addr).start()
    except KeyboardInterrupt:
        print("[SERVER] shutting down")
    finally:
        sock.close()

if __name__ == "__main__":
    start_server()
