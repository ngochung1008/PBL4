# Hướng Dẫn Sử Dụng Screenshot Storage

## Tổng Quan

Hệ thống tự động lưu trữ screenshots từ client khi họ gửi video frames lên server. Screenshots được tổ chức theo cấu trúc thư mục rõ ràng để dễ dàng quản lý và truy xuất khi cần thiết (ví dụ: khi client vi phạm).

## Cấu Trúc Thư Mục

```
screenshots/
├── client_username_1/
│   └── 2024/
│       ├── 12/
│       │   ├── 22/
│       │   │   ├── screen_145030_123456_1920x1080.jpg
│       │   │   ├── screen_145033_789012_1920x1080.jpg
│       │   │   └── ...
│       │   └── 23/
│       │       └── ...
│       └── ...
├── client_username_2/
│   └── ...
```

### Quy Ước Đặt Tên

- **Thư mục client**: Tên username của client
- **Thư mục năm**: YYYY (ví dụ: 2024)
- **Thư mục tháng**: MM (ví dụ: 12)
- **Thư mục ngày**: DD (ví dụ: 22)
- **File ảnh**: `screen_HHMMSS.jpg`
  - `HH`: Giờ (00-23)
  - `MM`: Phút (00-59)
  - `SS`: Giây (00-59)
  - Nếu có nhiều ảnh trong cùng 1 giây: `screen_HHMMSS_1.jpg`, `screen_HHMMSS_2.jpg`, ...

**Ví dụ**: `screen_143045.jpg` = ảnh chụp lúc 14:30:45

## Cơ Chế Hoạt Động

### 1. Tự Động Lưu Screenshots

Hệ thống thông minh lưu screenshots dựa trên 2 loại frames:

#### Frame FULL (Ảnh Đầy Đủ)
- Client gửi ảnh màn hình đầy đủ định kỳ (mỗi ~60 giây)
- Server **luôn lưu** frame FULL làm base image
- Dùng làm nền để ghép các frame RECT

#### Frame RECT (Ảnh Thay Đổi)
- Client gửi chỉ vùng thay đổi (delta) để tiết kiệm băng thông
- Server tự động **ghép RECT vào base image** để tạo ảnh hoàn chỉnh
- **Chỉ lưu khi thay đổi đủ lớn** (>20,000 pixels mặc định)
- **Throttling**: Chỉ lưu tối đa 1 ảnh/giây để tránh spam

### 2. Điều Kiện Lưu

Screenshot được lưu khi:
- ✅ Client đã đăng nhập thành công (authenticated)
- ✅ Nhận được frame FULL (luôn lưu) HOẶC
- ✅ Nhận được frame RECT với thay đổi > ngưỡng (mặc định 20,000 pixels)
- ✅ Đã qua ít nhất 1 giây kể từ lần lưu trước (tránh spam)

### 3. Ưu Điểm Của Cơ Chế Này

✅ **Tiết kiệm dung lượng**: Chỉ lưu khi có thay đổi đáng kể, không lưu mọi frame  
✅ **Đầy đủ thông tin**: Vẫn capture được mọi thay đổi quan trọng trên màn hình  
✅ **Không miss events**: RECT frames được ghép liên tục vào base image  
✅ **Hiệu quả**: Không cần lưu 30 FPS, chỉ lưu khi cần (VD: user click, gõ phím, đổi cửa sổ)  

### 4. Ví Dụ Thực Tế

**Kịch bản**: User đang làm việc trên máy tính

| Thời gian | Hành động | Frame Type | Pixels thay đổi | Lưu? | Lý do |
|-----------|-----------|------------|-----------------|------|-------|
| 14:30:00 | Mở Excel | FULL | N/A | ✅ Có | Frame FULL luôn lưu |
| 14:30:03 | Gõ text | RECT | 5,000 | ❌ Không | < 20,000 pixels |
| 14:30:06 | Scroll xuống | RECT | 80,000 | ✅ Có | > 20,000 pixels |
| 14:30:07 | Đổi tab | RECT | 150,000 | ❌ Không | Chưa đủ 1s (throttled) |
| 14:30:08 | Click cell | RECT | 25,000 | ✅ Có | > 20,000 + đã qua 1s |
| 14:31:00 | (định kỳ) | FULL | N/A | ✅ Có | Frame FULL định kỳ |

→ Kết quả: 4 screenshots được lưu trong 1 phút, capture đầy đủ các hoạt động quan trọng

### 5. Thông Tin Được Lưu

Mỗi file screenshot chứa:
- ✅ Ảnh màn hình **đầy đủ** của client (đã ghép RECT nếu cần)
- ✅ Timestamp chính xác đến giây (trong tên file)
- ✅ Metadata về client (username qua cấu trúc thư mục)
- ✅ Định dạng JPEG (quality 85%) để tiết kiệm dung lượng

### 6. Cấu Hình Ngưỡng Thay Đổi

Bạn có thể điều chỉnh ngưỡng thay đổi khi khởi tạo:

```python
# Mặc định: 20,000 pixels
storage = ScreenshotStorage(
    base_path="screenshots",
    change_threshold=20000
)

# Lưu nhiều hơn (nhạy hơn):
storage = ScreenshotStorage(change_threshold=5000)

# Lưu ít hơn (tiết kiệm hơn):
storage = ScreenshotStorage(change_threshold=100000)
```

**Hướng dẫn chọn ngưỡng**:
- **5,000 - 10,000**: Rất nhạy, lưu mọi thay đổi nhỏ (gõ phím, di chuột nhiều)
- **20,000 - 50,000**: Cân bằng (khuyến nghị) - Lưu các thay đổi có ý nghĩa
- **100,000 - 300,000**: Ít nhạy, chỉ lưu thay đổi lớn (đổi cửa sổ, scroll toàn màn hình)

## Sử Dụng API

### Khởi Tạo Storage (đã tích hợp trong SessionManager)

```python
from src.server.core.screenshot_storage import ScreenshotStorage

# Khởi tạo với đường dẫn tùy chỉnh
storage = ScreenshotStorage(base_path="screenshots")

# Hoặc dùng đường dẫn mặc định
storage = ScreenshotStorage()
```

### Lưu Screenshot Từ PDU

```python
# Lưu từ PDU đã parse
file_path = storage.save_screenshot_from_pdu(
    client_name="username123",
    pdu=parsed_pdu_dict
)

# Lưu từ raw payload (khuyến nghị - nhanh hơn)
file_path = storage.save_screenshot_from_raw(
    client_name="username123",
    raw_payload=raw_bytes
)
```

### Truy Xuất Screenshots

```python
# Lấy screenshots của client trong ngày hôm nay
screenshots = storage.get_client_screenshots("username123")

# Lấy screenshots trong ngày cụ thể
from datetime import datetime
date = datetime(2024, 12, 22)
screenshots = storage.get_client_screenshots("username123", date)

# Lấy danh sách tất cả client đã được lưu
all_clients = storage.get_all_client_names()
```

### Dọn Dẹp Screenshots Cũ

```python
# Xóa screenshots cũ hơn 30 ngày (mặc định)
storage.cleanup_old_screenshots()

# Xóa screenshots cũ hơn 90 ngày
storage.cleanup_old_screenshots(days=90)
```

## Quản Lý & Bảo Trì

### Kiểm Tra Dung Lượng

```powershell
# Kiểm tra tổng dung lượng thư mục screenshots
Get-ChildItem -Path screenshots -Recurse | Measure-Object -Property Length -Sum
```

### Backup Screenshots

```powershell
# Backup thư mục screenshots
Copy-Item -Path screenshots -Destination backup/screenshots_$(Get-Date -Format 'yyyyMMdd') -Recurse
```

### Tìm Kiếm Screenshots

```powershell
# Tìm tất cả screenshots của user trong tháng 12/2024
Get-ChildItem -Path screenshots/username123/2024/12 -Recurse -Filter *.jpg

# Tìm screenshots trong khoảng thời gian
Get-ChildItem -Path screenshots/username123/2024/12/22 -Filter screen_14*.jpg
```

## Tích Hợp Vào Workflow

### Kịch Bản Sử Dụng

#### 1. Phát Hiện Vi Phạm
Khi phát hiện client có hành vi vi phạm:
1. Ghi lại timestamp của sự kiện
2. Truy xuất screenshots tương ứng từ thư mục
3. Sử dụng làm bằng chứng

#### 2. Audit Trail
- Mỗi client có lịch sử screenshots theo thời gian
- Dễ dàng theo dõi hoạt động của client
- Hỗ trợ điều tra khi cần

#### 3. Compliance & Reporting
- Screenshots tự động được tổ chức theo ngày
- Hỗ trợ xuất báo cáo hoạt động
- Đáp ứng yêu cầu tuân thủ

## Lưu Ý Quan Trọng

### Hiệu Năng
- Việc lưu screenshot không block luồng chính
- Tốc độ lưu phụ thuộc vào I/O của disk
- Khuyến nghị sử dụng SSD cho hiệu năng tốt nhất

### Bảo Mật
- Screenshots chứa thông tin nhạy cảm
- Đảm bảo quyền truy cập thư mục `screenshots/` phù hợp
- Cân nhắc mã hóa thư mục nếu cần

### Dung Lượng
- Mỗi screenshot có kích thước ~100KB - 500KB (tùy độ phân giải)
- Với 1 client gửi 1 frame/3s = 28,800 frames/ngày
- Ước tính: ~3-10GB/client/ngày
- **Khuyến nghị**: Thiết lập cleanup tự động

### Privacy & GDPR
- Lưu trữ screenshots có thể liên quan đến quy định bảo vệ dữ liệu
- Thông báo cho users về việc lưu trữ
- Có chính sách xóa dữ liệu rõ ràng

## Cấu Hình Khuyến Nghị

### Production Environment

```python
# Trong server_constants.py hoặc config file
SCREENSHOT_STORAGE_ENABLED = True
SCREENSHOT_BASE_PATH = "screenshots"
SCREENSHOT_RETENTION_DAYS = 30  # Giữ screenshots trong 30 ngày
SCREENSHOT_AUTO_CLEANUP = True   # Tự động dọn dẹp
```

### Cron Job Cho Cleanup (Linux)

```bash
# Thêm vào crontab để chạy cleanup hàng ngày lúc 2h sáng
0 2 * * * /usr/bin/python3 /path/to/cleanup_screenshots.py
```

### Scheduled Task (Windows)

```powershell
# Tạo scheduled task để chạy cleanup
$action = New-ScheduledTaskAction -Execute "python" -Argument "cleanup_screenshots.py"
$trigger = New-ScheduledTaskTrigger -Daily -At 2am
Register-ScheduledTask -Action $action -Trigger $trigger -TaskName "ScreenshotCleanup"
```

## Troubleshooting

### Lỗi: Permission Denied
```
Solution: Đảm bảo quyền ghi vào thư mục screenshots/
chmod 755 screenshots/ (Linux)
icacls screenshots /grant Users:(OI)(CI)F (Windows)
```

### Lỗi: Disk Full
```
Solution: 
1. Chạy cleanup_old_screenshots()
2. Tăng SCREENSHOT_RETENTION_DAYS
3. Di chuyển thư mục screenshots sang disk khác
```

### Screenshots Không Được Lưu
```
Kiểm tra:
1. Client đã đăng nhập chưa?
2. PDU type có phải "full" không?
3. Logs có báo lỗi gì không?
4. Disk còn dung lượng không?
```

## Mở Rộng Tương Lai

### Tính Năng Có Thể Thêm

1. **Compression**
   - Nén screenshots cũ để tiết kiệm dung lượng
   - Sử dụng format WebP thay vì JPEG

2. **Cloud Storage**
   - Tự động upload lên S3/Azure Blob
   - Giảm tải cho local storage

3. **Metadata Database**
   - Lưu metadata vào database
   - Tìm kiếm nhanh hơn
   - Thêm tags và annotations

4. **Screenshot Analysis**
   - Phát hiện nội dung không phù hợp
   - OCR để tìm kiếm text trong ảnh
   - AI để phân loại hành vi

5. **API Endpoints**
   - REST API để truy xuất screenshots
   - Web interface để xem và quản lý
   - Export báo cáo PDF

## Tài Liệu Tham Khảo

- [Pillow Documentation](https://pillow.readthedocs.io/)
- [Python pathlib](https://docs.python.org/3/library/pathlib.html)
- [File I/O Best Practices](https://realpython.com/working-with-files-in-python/)
