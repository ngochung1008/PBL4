# server_network/server_transport.py
import socket
from client.common_network.tpkt_layer import TPKTLayer
from client.common_network.x224_handshake import X224Handshake

class ServerTransport:
    """Lớp đóng gói logic gửi/nhận gói TPKT qua socket."""

    @staticmethod
    def send(sock: socket.socket, data: bytes):
        """Gửi dữ liệu đã đóng gói TPKT."""
        try:
            pkt = TPKTLayer.pack(data)
            sock.sendall(pkt)
        except Exception as e:
            raise ConnectionError(f"Send error: {e}")

    @staticmethod
    def recv(sock: socket.socket):
        """Nhận và trả về payload của một gói TPKT."""
        hdr = X224Handshake.recv_all(sock, 4)
        ver, rsv, length = TPKTLayer.unpack_header(hdr)
        body = X224Handshake.recv_all(sock, length - 4)
        return body
