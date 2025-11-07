# File: server.py
"""
Server: accepts client screen sender connections and manager viewer connections.
- Listens on two ports (can be same port but we use same as client target port for clients and manager_port for managers)
- Performs simple X224-style handshake
- Parses TPKT frames and PDU payloads and forwards frames from clients to all connected managers
"""
import socket
import threading
import time
from server_network.x224_handshake import X224Handshake
from server_network.tpkt_layer import TPKTLayer
from server_network.pdu_parser import PDUParser

CLIENT_LISTEN_PORT = 33890
MANAGER_LISTEN_PORT = 33900

managers = set()
managers_lock = threading.Lock()


def broadcast_to_managers(tpkt_bytes):
    with managers_lock:
        for m in list(managers):
            try:
                m.sendall(tpkt_bytes)
            except Exception:
                try:
                    m.close()
                except Exception:
                    pass
                managers.remove(m)


class ClientHandler(threading.Thread):
    def __init__(self, conn, addr):
        super().__init__(daemon=True)
        self.conn = conn
        self.addr = addr
        self.client_id = None
        self.parser = PDUParser()

    def run(self):
        try:
            # handshake (read CONNECT and respond)
            if not X224Handshake.server_do_handshake(self.conn):
                print(f"[SERVER] Handshake failed for {self.addr}")
                self.conn.close()
                return
            # after handshake, continuously receive tpkt frames and forward to managers
            while True:
                hdr = self.conn.recv(4)
                if not hdr:
                    break
                ver, rsv, length = PTP = TPKTLayer.unpack_header(hdr)
                body = b""
                need = length - 4
                while need > 0:
                    chunk = self.conn.recv(need)
                    if not chunk:
                        raise ConnectionError("socket closed while receiving body")
                    body += chunk
                    need -= len(chunk)
                full_tpkt = hdr + body
                # optionally parse for logging
                try:
                    pdu = self.parser.parse_pdu(body)
                    if pdu['type'] == 'control':
                        print(f"[SERVER] Control from client: {pdu.get('message')}")
                    elif pdu['type'] in ('full', 'rect'):
                        print(f"[SERVER] Frame from client: type={pdu['type']} size={len(body)}")
                except Exception:
                    pass
                # forward raw tpkt to managers
                broadcast_to_managers(full_tpkt)
        except Exception as e:
            print(f"[SERVER] client handler error: {e}")
        finally:
            try:
                self.conn.close()
            except Exception:
                pass
            print(f"[SERVER] client disconnected {self.addr}")


class ManagerAcceptor(threading.Thread):
    def __init__(self, host='', port=MANAGER_LISTEN_PORT):
        super().__init__(daemon=True)
        self.host = host
        self.port = port

    def run(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((self.host, self.port))
        sock.listen(5)
        print(f"[SERVER] Manager acceptor listening on {self.host}:{self.port}")
        while True:
            conn, addr = sock.accept()
            print(f"[SERVER] Manager connected {addr}")
            # perform handshake (manager should do same CONNECT)
            try:
                if not X224Handshake.server_do_handshake(conn):
                    conn.close()
                    continue
            except Exception:
                conn.close()
                continue
            with managers_lock:
                managers.add(conn)


def start_server(host='', client_port=CLIENT_LISTEN_PORT, manager_port=MANAGER_LISTEN_PORT):
    # start manager acceptor
    ManagerAcceptor(host, manager_port).start()

    # accept clients
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((host, client_port))
    sock.listen(10)
    print(f"[SERVER] Client listener on {host}:{client_port}")
    try:
        while True:
            conn, addr = sock.accept()
            print(f"[SERVER] Client connected {addr}")
            ClientHandler(conn, addr).start()
    except KeyboardInterrupt:
        print("[SERVER] shutting down")
    finally:
        sock.close()


if __name__ == '__main__':
    start_server()