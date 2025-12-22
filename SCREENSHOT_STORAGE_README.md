# Screenshot Storage - Quick Start

## Giới Thiệu

Hệ thống tự động lưu screenshots từ client khi họ chia sẻ màn hình với server. Screenshots được tổ chức theo cấu trúc:

```
screenshots/
└── [tên_client]/
    └── [năm]/
        └── [tháng]/
            └── [ngày]/
                └── screen_[HHMMSS].jpg
```

**Ví dụ**: `screenshots/john_doe/2024/12/22/screen_143045.jpg`

## Tính Năng

✅ **Tự động lưu**: Screenshots được lưu tự động khi client gửi video frames  
✅ **Lưu khi có thay đổi**: Chỉ lưu khi có thay đổi đáng kể trên màn hình (>20,000 pixels)  
✅ **Ghép RECT frames**: Tự động ghép các frame RECT vào base image để có ảnh đầy đủ  
✅ **Tổ chức rõ ràng**: Cấu trúc thư mục theo tên client, năm, tháng, ngày  
✅ **Hiệu năng cao**: Không ảnh hưởng đến streaming (non-blocking)  
✅ **Tiết kiệm dung lượng**: Chỉ lưu khi cần thiết, format JPEG  
✅ **Dễ quản lý**: Tools để xem và dọn dẹp screenshots  
✅ **Tên file đơn giản**: Format `screen_HHMMSS.jpg` (giờ phút giây)  
✅ **Throttling thông minh**: Chỉ lưu tối đa 1 ảnh/giây để tránh spam  

## Cài Đặt

Không cần cài đặt thêm gì! Module đã được tích hợp sẵn vào server.

## Sử Dụng

### 1. Chạy Server (Screenshots Tự Động Lưu)

```bash
python run_server.py
```

Server sẽ tự động lưu screenshots vào thư mục `screenshots/` khi client gửi video frames.

### 2. Xem Screenshots

```bash
# Chế độ tương tác (interactive)
python view_screenshots.py

# Xem danh sách tất cả clients
python view_screenshots.py list

# Xem screenshots của client (hôm nay)
python view_screenshots.py username123

# Xem screenshots của client (ngày cụ thể)
python view_screenshots.py username123 2024-12-22

# Xem thống kê
python view_screenshots.py stats
```

### 3. Dọn Dẹp Screenshots Cũ

```bash
# Xóa screenshots cũ hơn 30 ngày (mặc định)
python cleanup_screenshots.py

# Xóa screenshots cũ hơn 7 ngày
python cleanup_screenshots.py 7

# Xóa screenshots cũ hơn 90 ngày
python cleanup_screenshots.py 90
```

## Ví Dụ Thực Tế

### Kịch Bản: Trích Xuất Bằng Chứng Vi Phạm

1. **Phát hiện vi phạm** lúc 14:30:45 ngày 22/12/2024
2. **Truy xuất screenshots**:
   ```bash (ví dụ: `screen_143045.jpg`)
   python view_screenshots.py suspicious_user 2024-12-22
   ```
3. **Tìm file** có timestamp gần 14:30:45
4. **Mở ảnh** để xem nội dung vi phạm

### Ví Dụ Output

```
================================================================================
SCREENSHOTS FOR: john_doe (2024-12-22)
================================================================================

Total: 125 screenshot(s)

1. screen_143045.jpg
   Size: 342.56 KB
   Path: screenshots/john_doe/2024/12/22/screen_143045.jpg

2. screen_143048.jpg
   Size: 298.42 KB
   Path: screenshots/john_doe/2024/12/22/screen_143048.jpg
...
```

## Cấu Hình

### Thay Đổi Ngưỡng Lưu Ảnh

Mặc định, hệ thống chỉ lưu ảnh khi có thay đổi **>20,000 pixels** (~140x140 vùng). Bạn có thể điều chỉnh:

Chỉnh sửa trong [src/server/core/session_manager.py](src/server/core/session_manager.py):

```python
# Mặc định: 20,000 pixels (cân bằng)
self.screenshot_storage = ScreenshotStorage(
    base_path="screenshots",
    change_threshold=20000
)

# Ví dụ: Lưu mọi thay đổi nhỏ (rất nhạy)
self.screenshot_storage = ScreenshotStorage(
    base_path="screenshots",
    change_threshold=5000  # Rất nhạy, lưu nhiều hơn
)

# Ví dụ: Chỉ lưu thay đổi rất lớn (tiết kiệm)
self.screenshot_storage = ScreenshotStorage(
    base_path="screenshots",
    change_threshold=100000  # Ít nhạy hơn, lưu ít hơn
)
```

**Lưu ý**: 
- Ngưỡng thấp = Lưu nhiều ảnh hơn = Tốn dung lượng
- Ngưỡng cao = Lưu ít ảnh hơn = Tiết kiệm dung lượng
- **20,000 pixels** ≈ vùng 140x140 (đủ để detect đổi tab, scroll, đổi cửa sổ)
- **5,000 pixels** ≈ vùng 70x70 (rất nhạy, capture mọi thay đổi)
- **100,000 pixels** ≈ vùng 316x316 (chỉ capture thay đổi rất lớn)
- Tham khảo: Màn hình 1920x1080 có ~2 triệu pixels

### Thay Đổi Đường Dẫn Lưu Trữ

Chỉnh sửa trong [src/server/core/session_manager.py](src/server/core/session_manager.py):

```python
# Mặc định: screenshots/
self.screenshot_storage = ScreenshotStorage(base_path="screenshots")

# Thay đổi:
self.screenshot_storage = ScreenshotStorage(base_path="/path/to/custom/folder")
```

### Tự Động Dọn Dẹp (Windows)

Tạo Scheduled Task:

```powershell
$action = New-ScheduledTaskAction -Execute "python" -Argument "D:\PBL\PBL4\cleanup_screenshots.py 30" -WorkingDirectory "D:\PBL\PBL4"
$trigger = New-ScheduledTaskTrigger -Daily -At 2am
Register-ScheduledTask -Action $action -Trigger $trigger -TaskName "ScreenshotCleanup" -Description "Auto cleanup old screenshots"
```

## Lưu Ý Quan Trọng

⚠️ **Dung lượng**: Mỗi client có thể tạo ra 3-10GB screenshots/ngày  
⚠️ **Bảo mật**: Screenshots chứa thông tin nhạy cảm, đảm bảo quyền truy cập phù hợp  
⚠️ **Privacy**: Thông báo cho users về việc lưu trữ screenshots  
⚠️ **Cleanup**: Thiết lập cleanup tự động để tránh đầy disk  

## Troubleshooting

### Screenshots Không Được Lưu?

1. Kiểm tra client đã đăng nhập thành công chưa
2. Xem logs của server: `log/server.log`
3. Kiểm tra quyền ghi vào thư mục `screenshots/`
4. Kiểm tra dung lượng disk còn trống

### Disk Đầy?

```bash
# Dọn dẹp ngay lập tức
python cleanup_screenshots.py 7  # Chỉ giữ 7 ngày gần nhất
```

## Tài Liệu Chi Tiết

Xem thêm: [SCREENSHOT_STORAGE_GUIDE.md](SCREENSHOT_STORAGE_GUIDE.md)

## API Reference

```python
from src.server.core.screenshot_storage import ScreenshotStorage

# Khởi tạo
storage = ScreenshotStorage(base_path="screenshots")

# Lưu từ raw payload
storage.save_screenshot_from_raw(client_name="user123", raw_payload=bytes_data)

# Lấy screenshots
screenshots = storage.get_client_screenshots("user123")
screenshots_date = storage.get_client_screenshots("user123", datetime(2024, 12, 22))

# Lấy danh sách clients
clients = storage.get_all_client_names()

# Cleanup
storage.cleanup_old_screenshots(days=30)
```

## License

Internal use only - PBL4 Project
