# common_network/security_layer_tls.py

import ssl
import socket
from typing import Optional, Tuple

""" Thiết lập phía Server """
# Tạo SSLContext cho server với các tùy chọn bảo mật
def create_server_context(certfile: str,
                          keyfile: str,
                          cafile: Optional[str] = None,
                          require_client_cert: bool = False) -> ssl.SSLContext:
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER) # khởi tạo context với vai trò là server
    try:
        context.minimum_version = ssl.TLSVersion.TLSv1_2
    except AttributeError:
        context.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1

    # Nếu có, nạp chứng chỉ server
    context.load_cert_chain(certfile=certfile, keyfile=keyfile)

    # Cấu hình xác thực client
    if require_client_cert:
        if cafile is None:
            raise ValueError("cafile required when require_client_cert=True")
        context.load_verify_locations(cafile=cafile) # Nạp CA để xác thực client
        context.verify_mode = ssl.CERT_REQUIRED # Yêu cầu client cung cấp chứng chỉ
    else:
        context.verify_mode = ssl.CERT_NONE # không yêu cầu chứng chỉ client

    try:
        context.set_ciphers("ECDHE+AESGCM:ECDHE+CHACHA20:ECDHE+AES256:!aNULL:!MD5:!RC4") # Ciphers ưu tiên
    except Exception:
        pass

    # Mitigation chống lại các cuộc tấn công nén
    try:
        context.options |= ssl.OP_NO_COMPRESSION # vô hiệu hóa nén
    except Exception:
        pass

    return context

# Đóng gói socket thô vào SSL socket với vai trò server (SSLContext đã tạo)
def server_wrap_socket(raw_sock: socket.socket,
                       context: ssl.SSLContext,
                       server_side: bool = True,
                       server_hostname: Optional[str] = None,
                       do_handshake: bool = True,
                       timeout: Optional[float] = None) -> ssl.SSLSocket:
    if timeout is not None:
        raw_sock.settimeout(timeout)
    ssl_sock = context.wrap_socket(raw_sock, server_side=server_side, do_handshake_on_connect=do_handshake) # đóng gói socket thô
    return ssl_sock

""" Thiết lập phía Client """ 
# Tạo SSLContext cho client với các tùy chọn bảo mật
def create_client_context(cafile: Optional[str] = None,
                          certfile: Optional[str] = None,
                          keyfile: Optional[str] = None,
                          check_hostname: bool = True) -> ssl.SSLContext:
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT) # khởi tạo context với vai trò là client
    try:
        context.minimum_version = ssl.TLSVersion.TLSv1_2
    except AttributeError:
        context.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1

    # Nạp CA để xác thực server
    if cafile: 
        context.load_verify_locations(cafile=cafile) # Nạp CA để xác thực server
        context.verify_mode = ssl.CERT_REQUIRED # yêu cầu xác thực server
    else:
        context.verify_mode = ssl.CERT_REQUIRED # mặc định vẫn yêu cầu xác thực server

    context.check_hostname = check_hostname # kiểm tra hostname của server trong chứng chỉ

    # Nạp chứng chỉ client nếu có
    if certfile and keyfile:
        context.load_cert_chain(certfile=certfile, keyfile=keyfile)

    try:
        context.options |= ssl.OP_NO_COMPRESSION # vô hiệu hóa nén
    except Exception:
        pass

    try:
        context.set_ciphers("ECDHE+AESGCM:ECDHE+CHACHA20:ECDHE+AES256:!aNULL:!MD5:!RC4") # Ciphers ưu tiên
    except Exception:
        pass

    return context

# Đóng gói socket thô vào SSL socket với vai trò client (SSLContext đã tạo)
def client_wrap_socket(raw_sock: socket.socket,
                       context: ssl.SSLContext,
                       server_hostname: Optional[str] = None,
                       timeout: Optional[float] = None,
                       do_handshake: bool = True) -> ssl.SSLSocket:
    if timeout is not None:
        raw_sock.settimeout(timeout)
    ssl_sock = context.wrap_socket(raw_sock, server_hostname=server_hostname, do_handshake_on_connect=do_handshake) 
    return ssl_sock

""" Tiện ích & Kiểm tra thông tin SSL socket """
# Lấy thông tin chứng chỉ của peer (client hoặc server)
def get_peer_certificate_info(ssl_sock: ssl.SSLSocket) -> dict:
    cert = ssl_sock.getpeercert()
    return cert

# Lấy thông tin cipher đang hoạt động của SSL socket
def get_active_cipher(ssl_sock: ssl.SSLSocket) -> Tuple[str, str, int]:
    c = ssl_sock.cipher()
    return c

""" Hàm tiện ích cho SSL socket (Gửi/Nhận dữ liệu) """
# Gửi toàn bộ data qua SSL socket
def ssl_send_all(ssl_sock: ssl.SSLSocket, data: bytes) -> None:
    totalsent = 0
    while totalsent < len(data):
        sent = ssl_sock.send(data[totalsent:])
        if sent is None or sent <= 0:
            raise ConnectionError("SSL socket send failed")
        totalsent += sent

# Nhận chính xác n bytes dữ liệu từ SSL socket
def ssl_recv_all(ssl_sock: ssl.SSLSocket, n: int, timeout: Optional[float] = None) -> bytes:
    if timeout is not None:
        ssl_sock.settimeout(timeout)
    data = bytearray()
    while len(data) < n:
        chunk = ssl_sock.recv(n - len(data))
        if not chunk:
            raise ConnectionError("ssl socket closed")
        data.extend(chunk)
    return bytes(data)
