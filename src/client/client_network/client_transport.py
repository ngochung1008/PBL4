# client_network/client_transport.py
import socket
from client.common_network.tpkt_layer import TPKTLayer
from client.common_network.x224_handshake import X224Handshake

class ClientTransport:
    """Lớp gửi nhận TPKT cho client."""

    @staticmethod
    def send(sock: socket.socket, data: bytes):
        pkt = TPKTLayer.pack(data)
        sock.sendall(pkt)

    @staticmethod
    def recv(sock: socket.socket):
        hdr = X224Handshake.recv_all(sock, 4)
        ver, rsv, length = TPKTLayer.unpack_header(hdr)
        return X224Handshake.recv_all(sock, length - 4)
