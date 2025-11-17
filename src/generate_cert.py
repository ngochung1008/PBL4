import datetime
from cryptography import x509

# --- SỬA LỖI Ở ĐÂY ---
# 'NameAttribute' đã được chuyển ra khỏi 'oid' trong các phiên bản mới
from cryptography.x509 import NameAttribute 
# --- KẾT THÚC SỬA LỖI ---

from cryptography.x509.oid import NameOID # Chúng ta sẽ dùng NameOID cho rõ ràng
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption, PublicFormat

# 1. Tạo Chìa khóa riêng (Private Key)
print("Đang tạo chìa khóa riêng (private key)...")
key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
    backend=default_backend()
)

# 2. Lưu Chìa khóa riêng (server.key)
# Đảm bảo bạn đang ở trong thư mục 'src' khi chạy
with open("server.key", "wb") as f:
    f.write(key.private_bytes(
        encoding=Encoding.PEM,
        format=PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=NoEncryption()
    ))

# 3. Tạo Chứng chỉ (Certificate) tự ký
print("Đang tạo chứng chỉ (certificate)...")
subject = issuer = x509.Name([
    x509.NameAttribute(NameOID.COUNTRY_NAME, u"VN"),
    x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"Da Nang"),
    x509.NameAttribute(NameOID.LOCALITY_NAME, u"Da Nang"),
    x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"PBL4 Development"),
    x509.NameAttribute(NameOID.COMMON_NAME, u"localhost"), # Quan trọng
])

cert = x509.CertificateBuilder().subject_name(
    subject
).issuer_name(
    issuer
).public_key(
    key.public_key()
).serial_number(
    x509.random_serial_number()
).not_valid_before(
    datetime.datetime.utcnow()
).not_valid_after(
    # Chứng chỉ có hạn 1 năm
    datetime.datetime.utcnow() + datetime.timedelta(days=365)
).add_extension( 
    x509.SubjectAlternativeName([x509.DNSName(u"localhost")]),
    critical=False,
).sign(key, hashes.SHA256(), default_backend())

# 4. Lưu Chứng chỉ (server.crt)
with open("server.crt", "wb") as f:
    f.write(cert.public_bytes(Encoding.PEM))

print("---")
print("Đã tạo thành công 2 file 'server.key' và 'server.crt' trong thư mục 'src'.")