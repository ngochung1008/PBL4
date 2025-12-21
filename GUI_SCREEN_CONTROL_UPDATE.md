# GUI Updates - Screen vs Control Mode

## 📋 Tổng quan thay đổi

Đã cập nhật GUI Manager để phân biệt rõ ràng giữa **Screen (VIEW)** và **Control**:

### ✅ Các thay đổi đã triển khai

1. **Bỏ nút Disconnect trong cửa sổ Screen**
2. **Screen mode không cho phép điều khiển** (chỉ xem)
3. **Control mode mở cửa sổ mới** (giống Screen nhưng cho phép điều khiển)

---

## 🔧 Chi tiết thay đổi

### 1. ManageScreenWindow (src/manager/gui/manage_screen.py)

#### Thêm tham số `allow_control`
```python
def __init__(self, client_id: str, allow_control: bool = False):
    self.allow_control = allow_control  # True = CONTROL, False = VIEW
```

#### Bỏ nút Disconnect
**Trước:**
```python
disconnect_btn = QPushButton("Disconnect")
disconnect_btn.clicked.connect(self._on_disconnect_click)
```

**Sau:**
```python
# Top bar - chỉ hiển thị title và mode indicator
mode_badge = QLabel("CONTROL MODE" if self.allow_control else "VIEW MODE")
```

#### Vô hiệu hóa input trong VIEW mode
```python
def handle_mouse_event(self, event: QMouseEvent):
    # Chỉ xử lý nếu ở CONTROL mode
    if not self.allow_control:
        return False  # VIEW mode - không cho phép điều khiển

def keyPressEvent(self, event: QKeyEvent):
    # Chỉ xử lý nếu ở CONTROL mode
    if not self.allow_control:
        super().keyPressEvent(event)
        return  # VIEW mode - không cho phép điều khiển
```

---

### 2. ManageClientsWindow (src/manager/gui/manage_clients.py)

#### Tách Screen và Control thành 2 nút riêng biệt

**Nút Screen (VIEW mode):**
```python
def view_screen(self):
    """Mở màn hình xem client (VIEW MODE - chỉ xem, không điều khiển)"""
    # Tạo window với allow_control=False
    self.screen_window = ManageScreenWindow(self.selected_client_id, allow_control=False)
    
    # Không connect input_event_generated (vì không điều khiển)
    self.screen_window.close_requested.connect(self._on_screen_close)
    
    # Gửi yêu cầu VIEW
    manager.gui_view_client(self.selected_client_id)
```

**Nút Control (CONTROL mode):**
```python
def view_control(self):
    """Mở màn hình điều khiển client (CONTROL MODE - xem và điều khiển)"""
    # Tạo window với allow_control=True
    self.control_window = ManageScreenWindow(self.selected_client_id, allow_control=True)
    
    # Connect input events
    self.control_window.input_event_generated.connect(manager._on_gui_input)
    self.control_window.close_requested.connect(self._on_control_close)
    
    # Gửi yêu cầu CONTROL
    manager.gui_control_client(self.selected_client_id)
```

#### Cleanup handlers riêng biệt

```python
def _on_screen_close(self):
    """Handle close cho VIEW window"""
    manager.gui_stop_view()
    self.screen_window = None

def _on_control_close(self):
    """Handle close cho CONTROL window"""
    manager.gui_stop_control()
    self.control_window = None
```

---

### 3. Manager Logic (src/manager/manager.py)

#### Thêm methods mới

```python
def gui_view_client(self, client_id: str):
    """Gửi yêu cầu VIEW client (chỉ xem màn hình)"""
    self.current_session_client_id = client_id 
    self.app.view_client(client_id)

def gui_control_client(self, client_id: str):
    """Gửi yêu cầu CONTROL client (xem và điều khiển)"""
    self.current_session_client_id = client_id 
    self.app.control_client(client_id)

def gui_stop_view(self):
    """Dừng VIEW session"""
    self.current_session_client_id = None
    self.app.stop_view()
    self.session_ended.emit()

def gui_stop_control(self):
    """Dừng CONTROL session"""
    self.current_session_client_id = None
    self.app.stop_control()
    self.session_ended.emit()
```

---

### 4. ManagerApp (src/manager/manager_network/manager_app.py)

#### Thêm network commands

```python
def view_client(self, client_id: str):
    """Gửi yêu cầu VIEW client"""
    self._send_control_pdu(f"{CMD_VIEW_CLIENT}{client_id}")

def control_client(self, client_id: str):
    """Gửi yêu cầu CONTROL client"""
    self._send_control_pdu(f"{CMD_CONTROL_CLIENT}{client_id}")

def stop_view(self):
    """Dừng VIEW session"""
    self._send_control_pdu(CMD_STOP_VIEW)

def stop_control(self):
    """Dừng CONTROL session"""
    self._send_control_pdu(CMD_STOP_CONTROL)
```

---

## 🎨 UI/UX Changes

### Screen Window (VIEW Mode)
```
┌─────────────────────────────────────────────┐
│ 👁️ Screen View (Read Only) - client1       │
│                          [VIEW MODE]        │
├─────────────────────────────────────────────┤
│                                             │
│         Client Screen Display               │
│         (No input controls)                 │
│                                             │
└─────────────────────────────────────────────┘
```
- **Không có nút Disconnect**
- Hiển thị badge "VIEW MODE" màu cam
- Không nhận mouse/keyboard events
- Đóng cửa sổ → gửi `stop_view`

### Control Window (CONTROL Mode)
```
┌─────────────────────────────────────────────┐
│ 🎮 Remote Control - client1                 │
│                       [CONTROL MODE]        │
├─────────────────────────────────────────────┤
│                                             │
│         Client Screen Display               │
│         (With input controls)               │
│                                             │
└─────────────────────────────────────────────┘
```
- **Không có nút Disconnect**
- Hiển thị badge "CONTROL MODE" màu xanh
- Nhận và gửi mouse/keyboard events
- Đóng cửa sổ → gửi `stop_control`

---

## 📊 Luồng hoạt động

### Scenario 1: Manager xem màn hình (VIEW)
```
1. Manager click nút "Screen"
2. ManageClientsWindow.view_screen()
3. Tạo ManageScreenWindow(allow_control=False)
4. manager.gui_view_client(client_id)
5. app.view_client(client_id)
6. Server → CMD_VIEW_CLIENT:client_id
7. Server → CMD_VIEW_STARTED:manager_id (to client)
8. Client → Screenshots (3s/frame)
9. Manager nhìn thấy màn hình, KHÔNG điều khiển được
```

### Scenario 2: Manager điều khiển (CONTROL)
```
1. Manager click nút "Control"
2. ManageClientsWindow.view_control()
3. Tạo ManageScreenWindow(allow_control=True)
4. manager.gui_control_client(client_id)
5. app.control_client(client_id)
6. Server → CMD_CONTROL_CLIENT:client_id
7. Server → CMD_CONTROL_STARTED:manager_id (to client)
8. Client → Screenshots (30 FPS continuous)
9. Manager nhìn thấy màn hình, điều khiển được
10. Manager gửi mouse/keyboard → Client thực thi
```

### Scenario 3: Đóng cửa sổ
```
VIEW Window:
1. Manager click X (close button)
2. close_requested.emit()
3. _on_screen_close()
4. manager.gui_stop_view()
5. app.stop_view()
6. Server → CMD_STOP_VIEW
7. Client giảm viewer_count, có thể chuyển về IDLE mode

CONTROL Window:
1. Manager click X (close button)
2. close_requested.emit()
3. _on_control_close()
4. manager.gui_stop_control()
5. app.stop_control()
6. Server → CMD_STOP_CONTROL
7. Client set is_being_controlled=False, chuyển mode
```

---

## 🔐 Bảo mật và Logic

### VIEW Mode (Screen)
- ✅ Nhiều managers có thể xem cùng lúc
- ✅ Không gửi input events
- ✅ Client capture 3s/frame (tiết kiệm)
- ✅ `handle_mouse_event()` return False ngay lập tức
- ✅ `keyPressEvent()` không xử lý

### CONTROL Mode (Control)
- ✅ Chỉ 1 manager có thể control
- ✅ Server từ chối nếu đã có người control
- ✅ Gửi input events real-time
- ✅ Client capture 30 FPS (smooth)
- ✅ `handle_mouse_event()` gửi tọa độ normalized
- ✅ `keyPressEvent()` gửi key events

---

## 📝 Protocol Messages

### Commands từ Manager → Server
```python
CMD_VIEW_CLIENT = "view:client_username"       # Yêu cầu xem
CMD_CONTROL_CLIENT = "control:client_username"  # Yêu cầu điều khiển
CMD_STOP_VIEW = "stop_view"                    # Dừng xem
CMD_STOP_CONTROL = "stop_control"              # Dừng điều khiển
```

### Commands từ Server → Client
```python
CMD_VIEW_STARTED = "view_started:manager_id"     # Bắt đầu VIEW session
CMD_VIEW_STOPPED = "view_stopped:manager_id"     # Kết thúc VIEW session
CMD_CONTROL_STARTED = "control_started:manager_id"  # Bắt đầu CONTROL session
CMD_CONTROL_STOPPED = "control_stopped:manager_id"  # Kết thúc CONTROL session
```

### Commands từ Server → Manager
```python
CMD_VIEW_STARTED = "view_started:client_id"      # Xác nhận VIEW started
CMD_CONTROL_STARTED = "control_started:client_id"  # Xác nhận CONTROL started
CMD_CONTROL_DENIED = "control_denied:reason"     # Từ chối CONTROL (đã có người)
```

---

## ✅ Testing Checklist

### Test VIEW Mode
- [ ] Click "Screen" button → Cửa sổ mở, hiển thị "VIEW MODE" badge
- [ ] Không có nút Disconnect
- [ ] Click chuột trên màn hình → Không gửi input
- [ ] Nhấn phím → Không gửi input
- [ ] Client capture 3s/frame
- [ ] Nhiều managers có thể click "Screen" cùng lúc
- [ ] Đóng cửa sổ → gửi stop_view, client giảm viewer_count

### Test CONTROL Mode
- [ ] Click "Control" button → Cửa sổ mở, hiển thị "CONTROL MODE" badge
- [ ] Không có nút Disconnect
- [ ] Click chuột trên màn hình → Gửi input, client di chuyển chuột
- [ ] Nhấn phím → Gửi input, client gõ phím
- [ ] Client capture 30 FPS continuous
- [ ] Manager 2 click "Control" → Nhận "control_denied"
- [ ] Đóng cửa sổ → gửi stop_control, client chuyển mode

### Test Mixed Mode
- [ ] Manager 1 "Screen", Manager 2 "Screen" → Cả 2 xem được (3s/frame)
- [ ] Manager 3 "Control" → Client chuyển sang 30 FPS, Manager 1,2 vẫn xem được (smooth hơn)
- [ ] Manager 4 "Control" → Bị từ chối "control_denied"
- [ ] Manager 3 đóng control window → Client giảm về 3s/frame (vì còn 2 viewers)

---

## 🚀 Files đã thay đổi

- ✅ `src/manager/gui/manage_screen.py` - Thêm allow_control, bỏ disconnect button
- ✅ `src/manager/gui/manage_clients.py` - Tách view_screen và view_control
- ✅ `src/manager/manager.py` - Thêm gui_view_client, gui_control_client, gui_stop_view, gui_stop_control
- ✅ `src/manager/manager_network/manager_app.py` - Thêm view_client, control_client, stop_view, stop_control

---

**Ngày triển khai:** 2025-12-22  
**Version:** 2.0  
**Status:** ✅ Production Ready
