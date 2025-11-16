# common_network/security_layer_tls.py
"""
TLS Security Layer helpers

Mục đích:
- Tạo SSLContext cho server và client (ưu tiên TLS 1.3 nếu có).
- Bọc socket TCP bằng TLS (server_wrap_socket, client_wrap_socket).
- Hàm helper kiểm tra chứng chỉ server/client và in thông tin cipher đang dùng.

Ghi chú quan trọng (bảo mật thực tế):
- TLS là cơ chế bảo mật chuẩn; bạn nên dùng TLS thay vì tự triển khai AES-CBC.
- Trước khi chạy, bạn cần có file chứng chỉ (PEM) và private key (PEM) cho server.
  Ví dụ tạo self-signed cert tạm thời (không dùng cho production):
    openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 365 -nodes \
      -subj "/CN=your-server-name"
- Để client xác thực server, client có thể dùng cafile trỏ tới cert.pem (self-signed),
  hoặc tới CA bundle nếu server có cert do CA ký.
"""

import ssl
import socket
from typing import Optional, Tuple

# -----------------------
# Server-side helpers
# -----------------------

def create_server_context(certfile: str,
                          keyfile: str,
                          cafile: Optional[str] = None,
                          require_client_cert: bool = False) -> ssl.SSLContext:
    """
    Tạo SSLContext cho server.
    - certfile, keyfile: đường dẫn tới PEM cert và private key (server).
    - cafile: đường dẫn tới CA (hoặc cert client) để verify client (nếu muốn).
    - require_client_cert: nếu True, server sẽ yêu cầu và verify client cert (mutual TLS).
    Trả về: ssl.SSLContext đã cấu hình.
    """
    # Sử dụng TLS server default: ưu tiên TLS 1.3 nếu hệ thống hỗ trợ.
    context = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
    # Không vô hiệu TLS 1.3 trừ khi bạn cần.
    # Load chứng chỉ server (X.509 PEM) và private key
    context.load_cert_chain(certfile=certfile, keyfile=keyfile)

    # Nếu muốn verify client cert, load CA (hoặc cert client) và yêu cầu verify
    if require_client_cert:
        if cafile is None:
            raise ValueError("cafile required when require_client_cert=True")
        context.load_verify_locations(cafile=cafile)
        context.verify_mode = ssl.CERT_REQUIRED
    else:
        # server không xác thực client certificate
        context.verify_mode = ssl.CERT_NONE

    # Tùy chọn bảo mật nâng cao (khuyến nghị)
    # - Không cho phép các ciphers yếu, chỉ dùng các cipher hiện đại (do OpenSSL mặc định tốt).
    # - Nếu muốn ép cipher, dùng context.set_ciphers(...)
    # - context.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1  # nếu cần
    return context

def server_wrap_socket(raw_sock: socket.socket,
                       context: ssl.SSLContext,
                       server_side: bool = True,
                       server_hostname: Optional[str] = None) -> ssl.SSLSocket:
    """
    Bọc socket đã accept() thành SSLSocket (server side).
    - raw_sock: socket object đã accept()
    - context: SSLContext từ create_server_context()
    Trả về ssl_sock (SSLSocket)
    """
    # server_side=True: bọc ở chế độ server
    ssl_sock = context.wrap_socket(raw_sock, server_side=server_side)
    # Lúc này handshake đã thực hiện tự động (blocking) hoặc khi lần đầu read/write.
    return ssl_sock

# -----------------------
# Client-side helpers
# -----------------------

def create_client_context(cafile: Optional[str] = None,
                          certfile: Optional[str] = None,
                          keyfile: Optional[str] = None,
                          check_hostname: bool = True) -> ssl.SSLContext:
    """
    Tạo SSLContext cho client.
    - cafile: file PEM chứa CA hoặc cert server (dùng khi self-signed)
    - certfile,keyfile: (tuỳ chọn) client cert cho mutual TLS
    - check_hostname: nếu True, client sẽ kiểm tra hostname khớp CN/SAN của cert server.
    """
    # purpose=SERVER_AUTH vì client xác thực server
    context = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH)

    if cafile:
        context.load_verify_locations(cafile=cafile)
    # Nếu cafile không cung cấp, context sẽ dùng hệ thống CA bundle mặc định
    # Bạn có thể tắt kiểm tra hostname bằng check_hostname=False (không khuyến nghị)
    context.check_hostname = check_hostname
    context.verify_mode = ssl.CERT_REQUIRED if cafile or check_hostname else ssl.CERT_NONE

    # Nếu client cần chứng chỉ để xác thực với server (mutual TLS)
    if certfile and keyfile:
        context.load_cert_chain(certfile=certfile, keyfile=keyfile)

    return context

def client_wrap_socket(raw_sock: socket.socket,
                       context: ssl.SSLContext,
                       server_hostname: Optional[str] = None,
                       timeout: Optional[float] = None) -> ssl.SSLSocket:
    """
    Bọc socket client bằng TLS.
    - raw_sock: socket đã connect(server_addr)
    - server_hostname: hostname của server (dùng cho SNI và kiểm tra hostname)
    - timeout: optional timeout (giữ nguyên nếu None)
    Trả về ssl_sock (SSLSocket) đã thực hiện handshake.
    """
    if timeout is not None:
        raw_sock.settimeout(timeout)
    # wrap_socket thực hiện handshake khi server_hostname != None hoặc on-demand.
    ssl_sock = context.wrap_socket(raw_sock, server_hostname=server_hostname)
    # Sau wrap_socket, handshake thường đã chạy (blocking).
    return ssl_sock

# -----------------------
# Helpers: send/recv wrappers & inspection
# -----------------------

def ssl_send_all(ssl_sock: ssl.SSLSocket, data: bytes) -> None:
    """
    Gửi toàn bộ dữ liệu qua SSLSocket (ghi đủ).
    """
    totalsent = 0
    while totalsent < len(data):
        sent = ssl_sock.send(data[totalsent:])
        if sent <= 0:
            raise ConnectionError("SSL socket send failed")
        totalsent += sent

def ssl_recv_all(ssl_sock: ssl.SSLSocket, n: int) -> bytes:
    """
    Đọc đúng n byte từ SSLSocket (blocking) — tương tự recv_all dùng với socket thô.
    """
    data = bytearray()
    while len(data) < n:
        chunk = ssl_sock.recv(n - len(data))
        if not chunk:
            raise ConnectionError("ssl socket closed")
        data.extend(chunk)
    return bytes(data)

def get_peer_certificate_info(ssl_sock: ssl.SSLSocket) -> dict:
    """
    Lấy thông tin chứng chỉ peer (server hoặc client) dạng dict (subject, issuer, san...).
    Sử dụng ssl_sock.getpeercert() (chỉ có khi verify_mode != CERT_NONE)
    """
    cert = ssl_sock.getpeercert()
    # cert là dict theo Python ssl, có 'subject', 'issuer', 'notAfter', 'subjectAltName', ...
    return cert

def get_active_cipher(ssl_sock: ssl.SSLSocket) -> Tuple[str, str, int]:
    """
    Trả về thông tin cipher hiện tại: (cipher_name, protocol_version, secret_bits)
    Ví dụ: ('TLS_AES_256_GCM_SHA384', 'TLSv1.3', 256)
    """
    c = ssl_sock.cipher()
    # .cipher() trả về tuple (cipher_name, protocol_version, secret_bits)
    return c

# -----------------------
# Example usage (docstring style)
# -----------------------
"""
Ví dụ Server:
    server_sock = socket.socket()
    server_sock.bind(('0.0.0.0', 8443))
    server_sock.listen(5)
    ctx = create_server_context(certfile='cert.pem', keyfile='key.pem')
    raw_conn, addr = server_sock.accept()
    ssl_conn = server_wrap_socket(raw_conn, ctx)
    # Bây giờ ssl_conn.recv()/send() đều an toàn (được TLS bảo vệ)
    cert_info = get_peer_certificate_info(ssl_conn)
    cipher = get_active_cipher(ssl_conn)
    print("Peer cert:", cert_info)
    print("Cipher:", cipher)

Ví dụ Client:
    raw = socket.create_connection(('server.example', 8443))
    ctx = create_client_context(cafile='cert.pem', check_hostname=False)
    ssl_sock = client_wrap_socket(raw, ctx, server_hostname='server.example')
    ssl_send_all(ssl_sock, b'hello via TLS')
    data = ssl_recv_all(ssl_sock, 16)

Lưu ý:
 - Với self-signed cert (cert.pem do bạn tạo bằng openssl), client phải đặt cafile=cert.pem
   hoặc tắt hostname verification (không khuyến nghị).
 - Trong production, server nên có cert do CA ký và client dùng hệ thống CA bundle.
"""
