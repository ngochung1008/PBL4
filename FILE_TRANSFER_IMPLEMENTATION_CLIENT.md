# File Transfer Implementation - Test Guide

## Những thay đổi đã thực hiện:

### 1. Manager Side (ĐÃ HOÀN THÀNH)
- ✅ Đã fix `_on_control_pdu()` trong `manager.py` để xử lý:
  - `file_transfer_start`: Gọi `handle_file_transfer_ack()` để bắt đầu gửi data chunks
  - `file_transfer_ack`: Cập nhật progress
  - `file_transfer_complete`: Xử lý hoàn thành
  - `file_transfer_error`: Xử lý lỗi

### 2. Client Side (MỚI HOÀN THÀNH)
- ✅ Đã tích hợp `ClientFileTransfer` vào `client_backend.py`:
  - Import ClientFileTransfer
  - Khởi tạo trong __init__
  - Thêm `_on_file_pdu()` handler
  - Thêm `_setup_file_transfer_callbacks()`
  - Thêm `gui_send_file()` method

- ✅ Đã tích hợp vào `client.py`:
  - Import ClientFileTransfer
  - Khởi tạo file_transfer instance
  - Thêm `_on_file_pdu()` handler
  - Xử lý file transfer commands trong `_on_control_pdu()`
  - Thêm `send_file()` method cho GUI

- ✅ Đã tạo `ClientFileTransferPanel` GUI:
  - Browse và chọn file
  - Send button với progress bar
  - Hiển thị danh sách file đã nhận
  - Open file và open folder buttons

- ✅ Đã tích hợp vào `ClientWindow`:
  - Thêm "File Transfer" button
  - Tạo file transfer window khi click
  - Connect signals và callbacks
  - Update progress, handle complete/error/received

### 3. File Transfer Flow (HOÀN CHỈNH)

#### Manager → Client:
1. Manager chọn file và click "Send File"
2. `ManagerFileTransfer.send_file()` gửi CMD_SEND_FILE request
3. Server tạo transfer record, gửi ACK "file_transfer_start:transfer_id"
4. Manager nhận ACK → `_on_control_pdu()` → `file_transfer.handle_file_transfer_ack()`
5. Manager gửi file data chunks (64KB/chunk) qua FILE channel
6. Server nhận chunks, forward đến client
7. Client nhận chunks qua `_on_file_pdu()` → `handle_file_pdu()`
8. Client lưu file vào `src/client/file_transfer/received/`
9. Client GUI hiển thị file mới trong danh sách

#### Client → Manager:
1. Client chọn file và click "Send File"
2. `ClientFileTransfer.send_file()` gửi CMD_SEND_FILE request (target_id="server")
3. Server tạo transfer record, gửi ACK "file_transfer_start:transfer_id"
4. Client nhận ACK → `_on_control_pdu()` → `file_transfer.handle_file_transfer_ack()`
5. Client gửi file data chunks qua FILE channel
6. Server forward chunks đến manager hiện tại
7. Manager nhận chunks → `handle_file_pdu()`
8. Manager lưu file vào `screenshots/{manager_username}/files/`
9. Manager GUI hiển thị file mới

## Cách Test:

### Test 1: Manager → Client
```bash
# Terminal 1: Start server
python run_server.py

# Terminal 2: Start manager
python run_manager.py
# Login → Connect to client → Click "File Transfer" button

# Terminal 3: Start client
python run_client.py
# Login → Start service → Click "File Transfer" button

# Actions:
1. Manager: Browse và chọn một file (ví dụ: ảnh hoặc PDF)
2. Manager: Click "Send File"
3. Kiểm tra progress bar chạy từ 0% → 100%
4. Client: Xem file mới xuất hiện trong "Received Files"
5. Client: Click "Open File" để mở file
```

### Test 2: Client → Manager
```bash
# Sau khi đã kết nối manager và client:

# Actions:
1. Client: Browse và chọn một file
2. Client: Click "Send File"
3. Kiểm tra progress bar chạy từ 0% → 100%
4. Manager: Xem file mới xuất hiện trong "Received Files"
5. Manager: Click "Open File" để mở file
```

### Test 3: Database Logging
```sql
-- Check file transfer history in MySQL
USE remote_control;
SELECT * FROM file_transfers ORDER BY created_at DESC LIMIT 10;

-- Should see records with:
-- sender_id, sender_type (manager/client)
-- receiver_id, receiver_type
-- filename, filesize, file_hash (SHA256)
-- status (pending → transferring → completed)
-- transferred_bytes
```

## Troubleshooting:

### Nếu progress bar stuck at 0%:
- Kiểm tra log: `[Manager] Control PDU từ client: file_transfer_start:2...`
- Xác nhận: `[ManagerFileTransfer] Received ACK, sending file data...` xuất hiện
- Nếu không: `_on_control_pdu()` chưa gọi `handle_file_transfer_ack()`

### Nếu client không thấy GUI file transfer:
- Click button "📁 File Transfer" trong ClientWindow
- Kiểm tra service đã start: "Trạng thái: Đã kết nối"
- Button chỉ enabled khi service running

### Nếu file transfer error:
- Kiểm tra network logs: PDU type 5 (FILE channel)
- Kiểm tra file size: Max 100MB (có thể tăng trong config)
- Kiểm tra permissions: Role "viewer" không được transfer file
- Kiểm tra file hash: SHA256 checksum phải match

## Files Changed:

### Modified:
- `src/manager/manager.py`: Fixed _on_control_pdu to handle file transfer
- `src/client/client_backend.py`: Added file transfer integration
- `src/client/client.py`: Added file transfer to Client class and ClientWindow
- `src/client/gui/file_panel.py`: Updated target_id and received files handling

### Created:
- `src/client/gui/file_transfer_panel.py`: Client file transfer GUI panel
- `FILE_TRANSFER_IMPLEMENTATION_CLIENT.md`: This documentation

## Next Steps:
1. Test manager → client transfer
2. Test client → manager transfer
3. Verify database logging
4. Test với nhiều file types (image, PDF, video)
5. Test với file lớn (>10MB)
6. Verify file integrity với SHA256 hash
