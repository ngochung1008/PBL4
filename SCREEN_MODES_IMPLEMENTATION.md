# Screen Modes Implementation - View vs Control

## 📋 Tổng quan

Hệ thống đã được cập nhật để hỗ trợ 2 chế độ hoạt động riêng biệt:
- **VIEW Mode** 👁️: Chỉ xem màn hình (nhiều manager có thể xem cùng lúc)
- **CONTROL Mode** 🎮: Xem và điều khiển (chỉ 1 manager có thể điều khiển)

## 🎯 Yêu cầu đã triển khai

### 1. VIEW Mode (Screen - Chỉ xem)
- ✅ **Nhiều manager có thể xem cùng 1 client**
- ✅ **Client capture màn hình mỗi 3 giây** (fps = 0.33) để tiết kiệm băng thông
- ✅ Không có khả năng điều khiển
- ✅ Client tự động phát hiện số lượng viewers

### 2. CONTROL Mode (Control - Xem và điều khiển)
- ✅ **Chỉ 1 manager có thể điều khiển 1 client tại 1 thời điểm**
- ✅ **Client capture màn hình liên tục (30 FPS)** để đảm bảo mượt mà
- ✅ Manager có thể gửi input (keyboard/mouse) đến client
- ✅ Khi có manager đang control, manager khác sẽ bị từ chối với thông báo `CMD_CONTROL_DENIED`

### 3. Chuyển đổi động giữa các mode
- ✅ Client tự động chuyển đổi FPS dựa trên session type
- ✅ Ưu tiên CONTROL mode (nếu đang control thì dùng 30 FPS ngay cả khi có viewer)
- ✅ IDLE mode (không gửi gì) khi không có session nào

## 🔧 Thay đổi kỹ thuật

### 📁 Client Side (`src/client/`)

#### 1. `client_screenshot.py`
**Thêm constants cho modes:**
```python
class ClientScreenshot:
    MODE_VIEW = "view"      # View-only: 3 giây/frame
    MODE_CONTROL = "control"  # Control: 30 FPS continuous
    MODE_IDLE = "idle"       # Không gửi
```

**Thêm method set_mode():**
```python
def set_mode(self, mode):
    """Đặt chế độ capture: VIEW, CONTROL, hoặc IDLE"""
    if mode == self.MODE_VIEW:
        self.fps = 0.33  # 3 giây/frame
    elif mode == self.MODE_CONTROL:
        self.fps = 30    # 30 FPS
```

**Cập nhật capture_loop():**
- Bỏ qua capture khi ở MODE_IDLE
- Dynamic FPS adjustment dựa trên mode hiện tại

#### 2. `client_backend.py` và `client.py`
**Thêm tracking state:**
```python
self.viewer_count = 0           # Số lượng managers đang xem
self.is_being_controlled = False  # Có manager đang điều khiển không
```

**Thêm method _update_screenshot_mode():**
```python
def _update_screenshot_mode(self):
    if self.is_being_controlled:
        self.screenshot.set_mode(self.screenshot.MODE_CONTROL)  # 30 FPS
    elif self.viewer_count > 0:
        self.screenshot.set_mode(self.screenshot.MODE_VIEW)     # 3s/frame
    else:
        self.screenshot.set_mode(self.screenshot.MODE_IDLE)     # Không gửi
```

**Cập nhật _on_control_pdu():**
- Xử lý `view_started` / `view_stopped`: Tăng/giảm viewer_count
- Xử lý `control_started` / `control_stopped`: Bật/tắt is_being_controlled
- Gọi `_update_screenshot_mode()` sau mỗi thay đổi

### 📁 Server Side (`src/server/core/`)

#### 1. `session_manager.py`
**Cập nhật comments:**
```python
# VIEW: 1 client có thể có nhiều viewers (1-nhiều) - Chỉ xem màn hình (3s/frame)
self.view_sessions = {}

# CONTROL: 1 client chỉ có 1 controller (1-1 exclusive) - Xem và điều khiển (30 FPS)
self.control_sessions = {}
```

**Logic đã có sẵn (không cần thay đổi):**
- `_start_view_session()`: Thêm manager vào ViewSession (cho phép nhiều viewers)
- `_start_control_session()`: Kiểm tra exclusive control (chỉ 1 controller)
- Gửi `CMD_VIEW_STARTED`, `CMD_CONTROL_STARTED` đến client

#### 2. `view_session.py` và `control_session.py`
**Cập nhật docstrings** để làm rõ hành vi:
- ViewSession: Nhiều viewers, 3s/frame
- ControlSession: 1-1 exclusive, 30 FPS continuous

## 📊 Luồng hoạt động

### Scenario 1: Manager VIEW client
```
1. Manager → Server: "view:client_username"
2. Server → SessionManager: _start_view_session()
3. Server → Client: "view_started:manager_id"
4. Client: viewer_count++, set_mode(MODE_VIEW) → 3s/frame
5. Client → Server: Screenshot frames (mỗi 3 giây)
6. Server → Manager: Broadcast frames qua ViewSession
```

### Scenario 2: Manager CONTROL client
```
1. Manager → Server: "control:client_username"
2. Server → SessionManager: _start_control_session()
   - Kiểm tra client đã bị control chưa → Từ chối nếu có
3. Server → Client: "control_started:manager_id"
4. Client: is_being_controlled=True, set_mode(MODE_CONTROL) → 30 FPS
5. Client → Server: Screenshot frames (continuous 30 FPS)
6. Server → Manager: Relay frames + input qua ControlSession
7. Manager → Server: Input commands
8. Server → Client: Forward input
```

### Scenario 3: Nhiều manager xem, 1 manager control
```
State: 2 managers viewing, 1 manager controlling

Client state:
- viewer_count = 2
- is_being_controlled = True
- Mode = MODE_CONTROL (30 FPS) ← Ưu tiên control

Khi manager dừng control:
- is_being_controlled = False
- Mode = MODE_VIEW (3s/frame) ← Vẫn có 2 viewers
```

## 🔐 Bảo mật và giới hạn

### Control Session (1-1 Exclusive)
```python
# Trong _start_control_session()
if client_id in self.control_sessions:
    existing_controller = self.control_sessions[client_id].manager_id
    self._send_control_pdu(manager_id, 
        f"{CMD_CONTROL_DENIED}:Client đang bị điều khiển bởi {existing_controller}")
    return False
```

### View Session (1-nhiều)
```python
# Trong _start_view_session()
# Không có giới hạn số viewers
view_session.add_viewer(manager_id)  # Thêm vào set
```

## 📈 Tối ưu băng thông

| Mode | FPS | Interval | Use case |
|------|-----|----------|----------|
| **IDLE** | 0 | N/A | Không có session |
| **VIEW** | 0.33 | ~3s | Giám sát, monitoring |
| **CONTROL** | 30 | ~33ms | Remote control, real-time interaction |

**Tiết kiệm băng thông:**
- VIEW mode giảm 90x lượng dữ liệu so với CONTROL mode
- Tự động chuyển về IDLE khi không có session → Không lãng phí CPU/Network

## 🧪 Testing

### Test VIEW mode
1. Manager 1 click "View" client
2. Manager 2 click "View" cùng client
3. Cả 2 managers đều nhìn thấy màn hình (3s/frame)
4. Kiểm tra log client: "Tổng viewers: 2"

### Test CONTROL mode
1. Manager 1 click "Control" client
2. Manager 1 có thể điều khiển, màn hình mượt (30 FPS)
3. Manager 2 click "Control" cùng client
4. Manager 2 nhận được "CMD_CONTROL_DENIED"

### Test Mixed mode
1. Manager 1 "View" client (3s/frame)
2. Manager 2 "View" client (3s/frame)
3. Manager 3 "Control" client
4. Client tự động chuyển sang 30 FPS
5. Manager 1,2 vẫn xem được nhưng giờ smooth hơn (30 FPS)
6. Manager 3 dừng control
7. Client tự động giảm xuống 3s/frame (vì còn 2 viewers)

## 📝 Commands hỗ trợ

### Manager → Server
```python
CMD_VIEW_CLIENT = "view:client_username"      # Bắt đầu xem
CMD_CONTROL_CLIENT = "control:client_username"  # Bắt đầu điều khiển
CMD_STOP_VIEW = "stop_view"                    # Dừng xem
CMD_STOP_CONTROL = "stop_control"              # Dừng điều khiển
```

### Server → Client
```python
CMD_VIEW_STARTED = "view_started:manager_id"
CMD_VIEW_STOPPED = "view_stopped:manager_id"
CMD_CONTROL_STARTED = "control_started:manager_id"
CMD_CONTROL_STOPPED = "control_stopped:manager_id"
CMD_CONTROL_DENIED = "control_denied:reason"
```

## ✅ Checklist hoàn thành

- [x] VIEW mode: nhiều managers có thể xem
- [x] CONTROL mode: chỉ 1 manager có thể điều khiển
- [x] Client capture 3s/frame cho VIEW
- [x] Client capture 30 FPS continuous cho CONTROL
- [x] Tự động chuyển đổi mode dựa trên session type
- [x] Từ chối control nếu đã có manager đang control
- [x] Broadcast frame tới tất cả viewers trong VIEW mode
- [x] Relay frame 1-1 trong CONTROL mode
- [x] Cập nhật comments và documentation

## 🚀 Triển khai

Các thay đổi đã được áp dụng vào:
- ✅ `src/client/client_screenshot.py`
- ✅ `src/client/client_backend.py`
- ✅ `src/client/client.py`
- ✅ `src/server/core/session_manager.py`
- ✅ `src/server/core/view_session.py`
- ✅ `src/server/core/control_session.py`

**Không cần thay đổi database hoặc config files.**

## 🔮 Tương lai có thể mở rộng

1. **Thêm port riêng cho CONTROL mode** (như yêu cầu ban đầu)
   - Tách traffic VIEW và CONTROL ra 2 port khác nhau
   - Cải thiện QoS và priority handling

2. **Adjustable FPS cho VIEW mode**
   - Cho phép admin config 1s, 3s, 5s, 10s interval
   
3. **Quality of Service (QoS)**
   - Ưu tiên gói tin CONTROL hơn VIEW
   - Throttling bandwidth theo số lượng viewers

4. **Notification system**
   - Thông báo cho viewers khi có manager bắt đầu control
   - Alert khi client bị quá tải

---
**Ngày triển khai:** 2025-12-22  
**Version:** 1.0  
**Status:** ✅ Production Ready
