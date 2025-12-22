# Hướng Dẫn Sử Dụng File Transfer

## Chuẩn Bị

### 1. Chạy Migration Database
Trước khi sử dụng, chạy migration để tạo bảng `file_transfers`:

```bash
python run_migrations.py
```

### 2. Kiểm Tra Cài Đặt
Chạy test để kiểm tra:

```bash
python test_file_transfer.py
```

## Cách Sử Dụng

### Bước 1: Khởi Động Server
```bash
python run_server.py
```

### Bước 2: Khởi Động Manager
```bash
python run_manager.py
```
- Đăng nhập với tài khoản manager
- Chọn client từ danh sách

### Bước 3: Khởi Động Client
```bash
python run_client.py
```
- Client tự động kết nối và xuất hiện trong danh sách manager

### Bước 4: Sử Dụng File Transfer

#### Từ Manager GUI:

1. **Chọn Client**: Click vào client trong danh sách bên trái
2. **Click Button "File Transfer"**: Ở thanh buttons phía trên
3. **Gửi File**:
   - Click "Chọn File" để browse file
   - File được chọn sẽ hiển thị
   - Click "Gửi File"
   - Thanh progress bar sẽ hiển thị tiến độ
4. **Nhận File**:
   - File từ client sẽ tự động hiện trong danh sách "File Đã Nhận"
   - Click vào file và chọn "Mở File" để xem
   - Hoặc "Mở Thư Mục" để xem folder chứa file

## Cấu Trúc File

### Manager
- **File nhận được lưu tại**: `manager_received_files/`
- Tự động tạo nếu chưa có
- Tránh ghi đè (thêm số vào tên file)

### Client
- **File nhận được lưu tại**: `received_files/`
- Tự động tạo nếu chưa có
- Tránh ghi đè (thêm số vào tên file)

### Database (Server)
- **Bảng**: `file_transfers`
- **Location**: MySQL database được config trong `config/server_config.py`
- Tất cả lịch sử transfer được lưu

## Tính Năng

### ✅ Manager → Client
- Chọn client
- Click "File Transfer"
- Chọn file và gửi
- Theo dõi progress
- Xem lịch sử file đã gửi

### ✅ Client → Manager
- Client có thể gửi file ngược lại manager
- Manager nhận và hiển thị trong danh sách

### ✅ Lịch Sử
- Mọi transfer được lưu trong database
- Có thể query để xem lịch sử:
  ```sql
  SELECT * FROM file_transfers ORDER BY created_at DESC;
  ```

## Giới Hạn

### File Size
- **Default**: 10MB
- Có thể thay đổi trong `config/server_config.py`:
  ```python
  max_file_size = 20 * 1024 * 1024  # 20MB
  ```

### Security
- File được verify bằng SHA256 hash
- Tên file được sanitize để tránh path traversal
- Size được validate trước khi chấp nhận

## Troubleshooting

### File Không Gửi Được

1. **Check connection**: Manager và Client đã kết nối server chưa?
2. **Check target**: Đã chọn client trong danh sách chưa?
3. **Check file size**: File có quá lớn không?
4. **Check logs**: 
   - Server: `log/server.log`
   - Manager/Client: Console output

### File Không Nhận Được

1. **Check folder**: Folder `manager_received_files/` hoặc `received_files/` có tồn tại không?
2. **Check permissions**: Có quyền ghi vào folder không?
3. **Check hash**: File có bị corrupt không? (check logs)

### Database Errors

1. **Check migration**: Đã chạy `python run_migrations.py` chưa?
2. **Check config**: `config/server_config.py` có đúng không?
3. **Check MySQL**: MySQL server có đang chạy không?

## Demo Flow

### Scenario: Manager gửi báo cáo cho Client

1. **Manager**: 
   - Khởi động `run_manager.py`
   - Đăng nhập
   - Chọn client "john_doe" trong danh sách
   - Click "File Transfer"
   - Chọn file "report.pdf"
   - Click "Gửi File"
   - Thấy progress bar chạy đến 100%
   - Thông báo "✅ Gửi file thành công!"

2. **Client (john_doe)**:
   - File "report.pdf" tự động xuất hiện trong GUI
   - Hoặc được lưu vào `received_files/report.pdf`

3. **Server**:
   - Lưu record trong `file_transfers` table:
     ```
     sender_id: admin
     sender_type: manager
     receiver_id: john_doe
     receiver_type: client
     filename: report.pdf
     status: completed
     ```

## Technical Details

### Luồng Data

```
Manager GUI
    ↓ (Click "Gửi File")
ManagerFileTransfer.send_file()
    ↓ (CMD_SEND_FILE)
ManagerApp.send_control_message()
    ↓ (Control PDU)
Server
    ↓ (Create DB record)
    ↓ (ACK)
ManagerFileTransfer.handle_file_transfer_ack()
    ↓ (File data chunks via CHANNEL_FILE)
Server.FileTransferHandler
    ↓ (Forward to receiver)
ClientReceiver
    ↓ (File PDU)
Client.file_transfer.handle_file_received()
    ↓ (Save to disk)
received_files/filename
```

### Commands

- `CMD_SEND_FILE`: Request transfer
- `CMD_FILE_TRANSFER_START`: ACK from server
- `CMD_FILE_TRANSFER_ACK`: Progress update
- `CMD_FILE_TRANSFER_COMPLETE`: Success
- `CMD_FILE_TRANSFER_ERROR`: Error

### Channels

- `CHANNEL_CONTROL` (3): Control messages
- `CHANNEL_FILE` (5): File data

## Tips

### Tối Ưu Transfer Speed
- Chunk size: 64KB (default)
- Có thể điều chỉnh trong code nếu cần

### Xem Lịch Sử Transfers
```python
from src.server.core.file_transfer_manager import FileTransferManager

ftm = FileTransferManager()
history = ftm.get_transfer_history("john_doe", "client", limit=10)
for t in history:
    print(f"{t['filename']}: {t['status']}")
```

### Debug Mode
Bật debug logs trong code:
```python
print(f"[Debug] Transfer #{transfer_id}: {progress}%")
```

## Support

- Xem logs: `log/server.log`
- Query database: `SELECT * FROM file_transfers;`
- Check file permissions
- Verify network connectivity

---

**Version**: 1.0  
**Last Updated**: December 22, 2025
