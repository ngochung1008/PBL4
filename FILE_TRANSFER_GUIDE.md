# Hướng Dẫn Sử Dụng Chức Năng Truyền File

## Tổng Quan

Hệ thống đã được bổ sung chức năng truyền file giữa Manager và Client thông qua Server. Tất cả lịch sử gửi file được lưu trữ tại server.

## Kiến Trúc

```
Manager/Client → Server (Xử lý & Lưu lịch sử) → Manager/Client
```

### Luồng Hoạt Động

1. **Gửi file**: Manager/Client gửi yêu cầu transfer tới Server
2. **Server xử lý**: 
   - Tạo bản ghi trong database (file_transfers table)
   - Nhận file data từ sender
   - Forward file tới receiver
   - Cập nhật trạng thái transfer
3. **Nhận file**: Receiver nhận file và lưu vào thư mục local

## Cài Đặt

### 1. Chạy Database Migration

Trước khi sử dụng, cần tạo bảng `file_transfers` trong database:

```bash
python run_migrations.py
```

Migration sẽ tạo bảng với các trường:
- `id`: Primary key
- `sender_id`, `sender_type`: Thông tin người gửi
- `receiver_id`, `receiver_type`: Thông tin người nhận
- `filename`, `filesize`: Thông tin file
- `file_hash`: SHA256 hash để verify
- `status`: Trạng thái (pending, sending, completed, failed)
- `transfer_started_at`, `transfer_completed_at`: Thời gian
- `created_at`: Timestamp

### 2. Cấu Hình

Trong `config/server_config.py`, có thể điều chỉnh:

```python
max_file_size = 10 * 1024 * 1024  # 10MB (mặc định)
```

## Sử Dụng

### Từ Phía Manager

```python
from src.manager.manager_file_transfer import ManagerFileTransfer

# Khởi tạo (trong ManagerApp)
file_transfer = ManagerFileTransfer(manager_app)

# Callback handlers (optional)
file_transfer.on_file_received = lambda filename, path, sender: print(f"Received: {filename}")
file_transfer.on_file_send_progress = lambda progress: print(f"Progress: {progress}%")
file_transfer.on_file_send_complete = lambda filename: print(f"Completed: {filename}")
file_transfer.on_file_send_error = lambda error: print(f"Error: {error}")

# Gửi file tới client
success = file_transfer.send_file(
    target_client_id="client_username",
    filepath="path/to/file.pdf"
)
```

### Từ Phía Client

```python
from src.client.client_file_transfer import ClientFileTransfer

# Khởi tạo (trong ClientBackend)
file_transfer = ClientFileTransfer(sender, receiver)

# Callback handlers (optional)
file_transfer.on_file_received = lambda filename, path, sender: print(f"Received: {filename}")
file_transfer.on_file_send_progress = lambda progress: print(f"Progress: {progress}%")
file_transfer.on_file_send_complete = lambda filename: print(f"Completed: {filename}")
file_transfer.on_file_send_error = lambda error: print(f"Error: {error}")

# Gửi file tới manager
success = file_transfer.send_file(
    target_id="manager_username",
    filepath="path/to/document.docx"
)
```

### GUI Integration

Trong GUI (file_panel.py):

```python
# Kết nối signal
file_panel.file_selected.connect(self.handle_file_send)

# Set target trước khi gửi
file_panel.set_target("target_username")

# Update progress
file_panel.update_send_progress(50)  # 50%

# Thêm file đã nhận vào danh sách
file_panel.add_received_file("document.pdf", "/path/to/saved/document.pdf")
```

## Xử Lý Trong Server

Server tự động xử lý các bước:

1. **Nhận yêu cầu** (`CMD_SEND_FILE`):
   ```
   send_file:target_id:filename:filesize:hash
   ```

2. **Tạo transfer record** trong database

3. **Gửi ACK** (`CMD_FILE_TRANSFER_START`):
   ```
   file_transfer_start:transfer_id
   ```

4. **Nhận file chunks** qua `CHANNEL_FILE` (PDU type "file")

5. **Forward file** tới receiver

6. **Hoàn thành** (`CMD_FILE_TRANSFER_COMPLETE`):
   ```
   file_transfer_complete:transfer_id:filename
   ```

## Lịch Sử Transfer

### Xem Lịch Sử Của Một User

```python
from src.server.core.file_transfer_manager import FileTransferManager

ftm = FileTransferManager()

# Lấy lịch sử của một entity
history = ftm.get_transfer_history(
    entity_id="username",
    entity_type="client",  # hoặc "manager"
    limit=50
)

for transfer in history:
    print(f"{transfer['filename']}: {transfer['status']}")
```

### Xem Tất Cả Lịch Sử (Admin)

```python
all_transfers = ftm.get_all_transfers(limit=100)
```

## Bảo Mật

### File Hash Verification

Mỗi file được tính SHA256 hash trước khi gửi. Server verify hash sau khi nhận:

```python
file_hash = hashlib.sha256(file_data).hexdigest()
```

### File Size Limit

Server kiểm tra kích thước file trước khi chấp nhận:

```python
if not file_transfer_manager.validate_file_size(filesize):
    return error
```

### Path Sanitization

Tên file được sanitize để tránh path traversal:

```python
safe_filename = os.path.basename(filename)
```

## Error Handling

### Các Loại Lỗi

1. **File không tồn tại**: Client check trước khi gửi
2. **File quá lớn**: Server từ chối ngay
3. **Hash mismatch**: Server báo lỗi và rollback
4. **Target không online**: Server báo lỗi ngay
5. **Network error**: Retry hoặc báo lỗi

### Commands

- `CMD_FILE_TRANSFER_ERROR`: Server báo lỗi
- `CMD_FILE_TRANSFER_ACK`: Server xác nhận nhận chunk
- `CMD_FILE_TRANSFER_COMPLETE`: Transfer thành công

## Thư Mục Lưu Trữ

### Client
- **Nhận file**: `received_files/`
- Tự động tạo nếu chưa có
- Tránh ghi đè bằng cách thêm số: `file_1.pdf`, `file_2.pdf`

### Manager
- **Nhận file**: `manager_received_files/`
- Logic tương tự client

## Ví Dụ Hoàn Chỉnh

### Manager gửi file tới Client

```python
# 1. Manager chọn file và target client
manager_app.file_transfer.send_file("john_doe", "report.pdf")

# 2. Server tạo record và gửi ACK
# 3. Manager gửi file data chunks
# 4. Server forward tới client "john_doe"
# 5. Client nhận và lưu vào "received_files/report.pdf"
# 6. Server cập nhật status = 'completed'
```

### Client gửi file tới Manager

```python
# 1. Client chọn file và target manager
client.file_transfer.send_file("admin", "screenshot.png")

# 2. Server xử lý và forward tới manager
# 3. Manager nhận file tại "manager_received_files/screenshot.png"
```

## Troubleshooting

### File không được gửi

1. Check connection: Manager/Client đã kết nối server chưa?
2. Check target: Target có online không?
3. Check file size: File có vượt quá `max_file_size` không?
4. Check logs: Xem log server để biết lỗi chi tiết

### File bị corrupted

- Check hash: Verify SHA256 hash
- Check network: Có packet loss không?
- Check chunks: Tất cả chunks đã nhận đủ chưa?

### Database errors

- Check migration: Đã chạy `run_migrations.py` chưa?
- Check connection: Database config có đúng không?
- Check permissions: User có quyền CREATE TABLE không?

## Performance

### Chunking

File được chia nhỏ thành chunks 64KB để:
- Tránh timeout
- Hiển thị progress
- Dễ retry nếu lỗi

### Concurrency

- Mỗi transfer có unique `transfer_id`
- Lock để tránh race condition
- Thread-safe với `threading.Lock()`

## Future Enhancements

- [ ] Resume interrupted transfers
- [ ] Compression trước khi gửi
- [ ] Encryption end-to-end
- [ ] Multiple file selection
- [ ] Folder transfer support
- [ ] Transfer speed limit
- [ ] Transfer history UI
- [ ] File preview trong GUI

## API Reference

### FileTransferManager (Server)

```python
create_transfer_record(sender_id, sender_type, receiver_id, receiver_type, filename, filesize, file_hash)
update_transfer_status(transfer_id, status, error_message)
get_transfer_history(entity_id, entity_type, limit)
get_all_transfers(limit)
calculate_file_hash(file_data)
validate_file_size(filesize)
```

### ClientFileTransfer

```python
send_file(target_id, filepath)
handle_file_transfer_ack(transfer_id)
handle_file_received(metadata, file_data)
handle_transfer_complete(transfer_id, filename)
handle_transfer_error(error_msg)
```

### ManagerFileTransfer

```python
send_file(target_client_id, filepath)
handle_file_transfer_ack(transfer_id)
handle_file_received(metadata, file_data)
handle_transfer_complete(transfer_id, filename)
handle_transfer_error(error_msg)
```

## Support

Nếu gặp vấn đề, check:
1. Server logs: `log/server.log`
2. Database: Query `file_transfers` table
3. File permissions: Check write access tới `received_files/`
4. Network: Check firewall, ports
