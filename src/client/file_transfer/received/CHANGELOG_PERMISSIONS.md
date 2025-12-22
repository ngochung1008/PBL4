# TỔNG HỢP CÁC THAY ĐỔI - HỆ THỐNG PHÂN QUYỀN CLIENT

## 📋 Tổng quan
Đã thêm hệ thống phân quyền hoàn chỉnh cho Client, dựa trên thông tin Role từ database.

## 📁 Files đã thay đổi/tạo mới

### 1. **src/client/client.py** ✏️ (Đã sửa đổi)
**Các thay đổi chính:**
- ✅ Thêm tham số `user_info` vào `__init__()`
- ✅ Lưu thông tin `user_id`, `username`, `role` từ database
- ✅ Khởi tạo `ClientPermissions(role)` để quản lý quyền
- ✅ Kiểm tra quyền trước khi gán callbacks:
  - `can_receive_remote_input()` → cho phép điều khiển từ xa
  - `can_transfer_file()` → cho phép truyền file
  - `can_see_cursor()` → hiển thị cursor
- ✅ Sửa logic login để gửi: `login:user_id:username:role`
- ✅ Thêm monitoring level dựa trên role (high/medium/none)
- ✅ Thêm hàm `_on_input_pdu_blocked()` và `_on_file_blocked()` để xử lý khi bị chặn

**Dòng code quan trọng:**
```python
# Line ~33-37: Khởi tạo permissions
self.user_info = user_info or {}
self.user_id = self.user_info.get('UserID', 'unknown')
self.username = self.user_info.get('Username', 'client')
self.role = self.user_info.get('Role', 'user')
self.permissions = ClientPermissions(self.role)

# Line ~76-90: Kiểm tra quyền cho callbacks
if self.permissions.can_receive_remote_input():
    self.network.on_input_pdu = self.input_handler.handle_input_pdu
else:
    self.network.on_input_pdu = self._on_input_pdu_blocked
```

---

### 2. **src/client/client_permissions.py** 🆕 (Mới tạo)
**Module quản lý phân quyền**

**Nội dung:**
- ✅ Class `ClientPermissions`: Quản lý permissions theo role
- ✅ Dictionary `ROLE_PERMISSIONS`: Định nghĩa quyền cho từng role
- ✅ Các method kiểm tra quyền:
  - `can_share_screen()`
  - `can_receive_remote_input()`
  - `can_transfer_file()`
  - `is_monitored()`
  - `can_see_cursor()`
  - `get_monitoring_level()`
- ✅ Hàm tiện ích: `check_permission()`, `get_role_permissions()`

**Định nghĩa permissions:**
```python
ROLE_PERMISSIONS = {
    'admin': {
        'can_share_screen': True,
        'can_receive_remote_input': True,
        'can_transfer_file': True,
        'is_monitored': False,  # ← KHÔNG bị giám sát
        'can_see_cursor': True,
        'monitoring_level': 'none',
    },
    'user': {
        'can_share_screen': True,
        'can_receive_remote_input': True,
        'can_transfer_file': True,
        'is_monitored': True,  # ← Bị giám sát
        'can_see_cursor': True,
        'monitoring_level': 'medium',
    },
    'viewer': {
        'can_share_screen': True,
        'can_receive_remote_input': False,  # ← KHÔNG điều khiển
        'can_transfer_file': False,         # ← KHÔNG truyền file
        'is_monitored': True,
        'can_see_cursor': False,
        'monitoring_level': 'high',
    }
}
```

---

### 3. **PERMISSIONS_README.md** 🆕 (Mới tạo)
**Tài liệu hướng dẫn chi tiết**

**Nội dung:**
- ✅ Giải thích chi tiết 3 role: admin, user, viewer
- ✅ Bảng so sánh quyền hạn
- ✅ Cấu trúc database (bảng Users)
- ✅ Cách thức hoạt động (flow chart)
- ✅ Ví dụ sử dụng code
- ✅ Hướng dẫn test và troubleshooting
- ✅ Cách mở rộng thêm role/permission mới

---

### 4. **test_permissions.py** 🆕 (Mới tạo)
**Script test hệ thống phân quyền**

**Chức năng:**
- ✅ Test tất cả 3 role (admin, user, viewer)
- ✅ Test các hàm tiện ích
- ✅ Test các kịch bản thực tế
- ✅ Mô phỏng user_info từ database
- ✅ Hiển thị monitoring levels và blacklist

**Chạy test:**
```bash
python test_permissions.py
```

---

### 5. **demo_client_roles.py** 🆕 (Mới tạo)
**Script demo client với các role**

**Chức năng:**
- ✅ Interactive menu chọn role (admin/user/viewer)
- ✅ Hiển thị permissions của role đã chọn
- ✅ Khởi động client với role đó
- ✅ Dễ dàng test các role khác nhau

**Chạy demo:**
```bash
python demo_client_roles.py
```

---

## 🎯 Các Role và Quyền hạn

### 🔴 ADMIN
| Quyền hạn | Trạng thái |
|-----------|------------|
| Screen Share | ✅ |
| Remote Input | ✅ |
| File Transfer | ✅ |
| Is Monitored | ❌ |
| Show Cursor | ✅ |
| Monitoring Level | 🟢 none |

### 🟠 USER
| Quyền hạn | Trạng thái |
|-----------|------------|
| Screen Share | ✅ |
| Remote Input | ✅ |
| File Transfer | ✅ |
| Is Monitored | ✅ |
| Show Cursor | ✅ |
| Monitoring Level | 🟠 medium |

### 🔵 VIEWER
| Quyền hạn | Trạng thái |
|-----------|------------|
| Screen Share | ✅ |
| Remote Input | ❌ |
| File Transfer | ❌ |
| Is Monitored | ✅ |
| Show Cursor | ❌ |
| Monitoring Level | 🔴 high |

---

## 💡 Cách sử dụng

### 1. Trong Database
```sql
-- Tạo user với role cụ thể
INSERT INTO Users (UserID, Username, PasswordHash, FullName, Email, Role)
VALUES ('user_001', 'john_doe', 'hash...', 'John Doe', 'john@test.com', 'user');

-- Thay đổi role
UPDATE Users SET Role = 'admin' WHERE UserID = 'user_001';
```

### 2. Trong Code
```python
# Lấy user info từ database (qua auth)
user_info = client_connection.client_profile(token)

# user_info = {
#     'UserID': 'user_001',
#     'Username': 'john_doe',
#     'Role': 'user',  # ← Từ database
#     ...
# }

# Khởi tạo client với user_info
from src.client.client import Client
client = Client(host, port, user_info=user_info)
client.start()
```

### 3. Test nhanh
```bash
# Test permissions system
python test_permissions.py

# Demo client với role
python demo_client_roles.py
```

---

## 🔄 Luồng hoạt động

```
[User Login] 
    ↓
[Auth Server] → Trả về token + user_info (có Role)
    ↓
[ClientWindow.__init__(user, token)]
    ↓
[ClientWindow.start_client_service()]
    ↓
[Client.__init__(host, port, user_info=self.user)]  ← Truyền user_info
    ↓
[Client tạo ClientPermissions(role)]
    ↓
[Client áp dụng permissions:]
    - Nếu can_receive_remote_input() → Allow remote control
    - Nếu can_transfer_file() → Allow file transfer
    - Nếu is_monitored() → Enable monitoring
    - Nếu can_see_cursor() → Show cursor
    ↓
[Client gửi: login:user_id:username:role]
    ↓
[Server nhận và xử lý theo role]
```

---

## ⚙️ Monitoring System

### Blacklist cơ bản (MEDIUM - User)
- Web phim lậu: phimmoi, phim hay
- Web cá độ: bet88, w88, cá cược, nhà cái
- Web bóng đá lậu: xoilac, trực tiếp bóng đá
- Nội dung 18+: sex, 18+

### Blacklist mở rộng (HIGH - Viewer)
- Tất cả blacklist cơ bản
- **Thêm:** game, facebook, youtube, netflix, spotify

### Cách thức giám sát
```python
# Trong _monitor_loop()
if not self.permissions.is_monitored():
    return  # Admin không bị giám sát

monitoring_level = self.permissions.get_monitoring_level()

if monitoring_level == 'high':
    # Thêm các từ khóa nghiêm ngặt hơn
    blacklist_keywords.extend(['game', 'facebook', 'youtube', ...])

# Phát hiện vi phạm
if bad_word in window_title:
    msg = f"security_alert:Web Cấm ({bad_word})|Đang truy cập: {title}"
    self.network.send_control_pdu(msg)
```

---

## 🧪 Kiểm tra

### Kiểm tra syntax
```bash
python -m py_compile src/client/client.py
python -m py_compile src/client/client_permissions.py
```

### Chạy test
```bash
python test_permissions.py
```

### Demo client
```bash
python demo_client_roles.py
```

---

## 📦 Các file liên quan

```
PBL4/
├── src/
│   └── client/
│       ├── client.py                    ✏️ Đã sửa
│       └── client_permissions.py        🆕 Mới tạo
├── database/
│   └── schema.sql                       (Có Role field)
├── PERMISSIONS_README.md                🆕 Mới tạo
├── test_permissions.py                  🆕 Mới tạo
└── demo_client_roles.py                 🆕 Mới tạo
```

---

## ✅ Checklist hoàn thành

- [x] Thêm phân quyền vào Client class
- [x] Tạo module ClientPermissions
- [x] Kiểm tra quyền cho remote input
- [x] Kiểm tra quyền cho file transfer
- [x] Kiểm tra quyền cho cursor tracking
- [x] Điều chỉnh monitoring theo role
- [x] Gửi thông tin role lên server khi login
- [x] Xử lý khi bị chặn quyền (blocked handlers)
- [x] Tạo tài liệu hướng dẫn chi tiết
- [x] Tạo script test đầy đủ
- [x] Tạo demo client interactive
- [x] Test syntax không lỗi
- [x] Chạy test thành công

---

## 🚀 Bước tiếp theo

1. **Test với database thật:**
   - Tạo users trong database với các role khác nhau
   - Đăng nhập qua GUI và test permissions

2. **Server-side validation:**
   - Server cần validate role khi nhận login command
   - Server cần từ chối các action không được phép theo role

3. **Logging:**
   - Log tất cả các action bị chặn vào database
   - Tạo báo cáo vi phạm

4. **UI Enhancements:**
   - Hiển thị role và permissions trong GUI
   - Vô hiệu hóa các button không được phép

---

## 📞 Liên hệ/Hỗ trợ

Nếu có vấn đề, xem:
- `PERMISSIONS_README.md` - Tài liệu chi tiết
- `test_permissions.py` - Test và debug
- `demo_client_roles.py` - Demo các role

---

**Ngày tạo:** 2025-01-15
**Phiên bản:** 1.0
**Trạng thái:** ✅ Hoàn thành
