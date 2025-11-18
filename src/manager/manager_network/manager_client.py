import socket
import ssl
from common_network.x224_handshake import X224Handshake, CONFIRM_MAGIC
from common_network.security_layer_tls import create_client_context, client_wrap_socket

class ManagerClient:
    """
    Kết nối manager -> server.
    Thực hiện X224 Handshake, sau đó bọc TLS/SSL.
    """

    def __init__(self, host: str, port: int, manager_id: str = "manager1"):
        self.host = host
        self.port = port
        self.manager_id = manager_id
        self.sock = None # Sẽ là SSLSocket sau khi kết nối

    def connect(self, cafile: str, timeout: float = 10.0) -> bool:
        raw_sock = None
        try:
            # 1. Kết nối socket thô (raw)
            raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            raw_sock.settimeout(timeout)
            raw_sock.connect((self.host, self.port))

            # 2. Thực hiện X224 Handshake (trên socket thô)
            resp = X224Handshake.client_send_connect(raw_sock, self.manager_id, timeout=timeout)
            
            if not (isinstance(resp, bytes) and resp.startswith(CONFIRM_MAGIC)):
                print("[ManagerClient] Handshake X224 thất bại, resp:", resp)
                raw_sock.close()
                return False

            print("[ManagerClient] Handshake X224 thành công.")

            # 3. Tạo TLS Context
            tls_context = create_client_context(cafile=cafile, check_hostname=False)

            # 4. Bọc (Wrap) socket thô lên SSLSocket
            self.sock = client_wrap_socket(
                raw_sock,
                tls_context,
                server_hostname=self.host, # Dùng cho SNI, nhưng bỏ qua kiểm tra
                timeout=timeout,
                do_handshake=True
            )
            
            # Chuyển về chế độ blocking cho receiver
            self.sock.settimeout(None)
            print(f"[ManagerClient] Kết nối TLS thành công tới {self.host}:{self.port}")
            return True

        except ssl.SSLError as e:
            print(f"[ManagerClient] Lỗi TLS Handshake: {e}. (Kiểm tra file '{cafile}')")
        except Exception as e:
            print(f"[ManagerClient] Lỗi kết nối: {e}")
        
        # Dọn dẹp nếu thất bại
        if self.sock:
            self.sock.close()
            self.sock = None
        if raw_sock:
            raw_sock.close()
            
        return False

    def close(self):
        if self.sock:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
            except: pass
            try:
                self.sock.close()
            except: pass
            self.sock = None