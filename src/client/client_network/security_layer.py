# client_network/security_layer.py

try:
    from Crypto.Cipher import AES
    from Crypto.Random import get_random_bytes
    AES_AVAILABLE = True
except Exception:
    AES_AVAILABLE = False

# Hỗ trợ mã hóa AES-CBC (tùy chọn)
class SecurityLayer:
    def __init__(self, use_encryption=False):
        self.use_encryption = use_encryption and AES_AVAILABLE
        if self.use_encryption:
            self.key = get_random_bytes(16)
            print("[CLIENT_NETWORK] SECURITY AES enabled, key:", self.key.hex())
        else:
            self.key = None

    def encrypt(self, data):
        if not self.use_encryption:
            return data
        iv = get_random_bytes(16)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        pad_len = 16 - (len(data) % 16)
        data_padded = data + bytes([pad_len]) * pad_len
        return iv + cipher.encrypt(data_padded)

    def decrypt(self, data):
        if not self.use_encryption:
            return data
        iv, ct = data[:16], data[16:]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        pt_padded = cipher.decrypt(ct)
        pad_len = pt_padded[-1]
        return pt_padded[:-pad_len]
