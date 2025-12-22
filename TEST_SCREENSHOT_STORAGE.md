# Hướng Dẫn Test Screenshot Storage

## Bước 1: Chạy Server

```bash
python run_server.py
```

Server sẽ tự động lưu screenshots vào thư mục `screenshots/`

## Bước 2: Chạy Client

```bash
python run_client.py
```

Đăng nhập và bắt đầu chia sẻ màn hình.

## Bước 3: Chạy Manager (để kích hoạt screen sharing)

```bash
python run_manager.py
```

Kết nối tới client để kích hoạt việc gửi video frames.

## Bước 4: Kiểm Tra Screenshots

### Kiểm tra thư mục
```bash
# Xem cấu trúc thư mục
dir screenshots /s

# Hoặc trên Linux/Mac
ls -R screenshots
```

### Sử dụng tool xem
```bash
# Chế độ interactive
python view_screenshots.py

# Xem danh sách clients
python view_screenshots.py list

# Xem screenshots của client
python view_screenshots.py <username>
```

## Kiểm Tra Logs

Server sẽ in ra logs khi lưu screenshots:

```
[ScreenshotStorage] Updated base image for username123: 1920x1080
[ScreenshotStorage] ✓ Saved screenshot: screenshots/username123/2024/12/22/screen_143045.jpg

[ScreenshotStorage] Significant change detected for username123: 85000 pixels
[ScreenshotStorage] ✓ Saved screenshot: screenshots/username123/2024/12/22/screen_143052.jpg
```

## Kiểm Tra Các Trường Hợp

### Test 1: Frame FULL
- ✅ Khi client mới kết nối và gửi frame đầu tiên
- ✅ Mỗi ~60 giây client sẽ gửi FULL frame
- **Kết quả**: Screenshot được lưu ngay lập tức

### Test 2: Frame RECT với thay đổi lớn
- ✅ Scroll trang web
- ✅ Đổi tab/cửa sổ
- ✅ Mở ứng dụng mới
- **Kết quả**: Screenshot được lưu nếu thay đổi > 20,000 pixels

### Test 3: Frame RECT với thay đổi nhỏ
- ❌ Gõ text trong textbox nhỏ
- ❌ Di chuyển chuột
- ❌ Click button nhỏ
- **Kết quả**: Screenshot KHÔNG được lưu (thay đổi < 20,000 pixels)

### Test 4: Throttling
- Tạo nhiều thay đổi liên tục trong < 1 giây
- **Kết quả**: Chỉ lưu 1 screenshot/giây

## Điều Chỉnh Để Test

### Để thấy nhiều screenshots hơn (test purpose)

Chỉnh sửa `src/server/core/session_manager.py`:

```python
# Giảm ngưỡng xuống 5,000 để rất nhạy
self.screenshot_storage = ScreenshotStorage(
    base_path="screenshots",
    change_threshold=5000  # Giảm từ 20,000 xuống 5,000
)
```

Chỉnh sửa `src/server/core/screenshot_storage.py`:

```python
# Trong method _save_image, giảm throttling
if time_since_last_save < 0.5:  # Giảm từ 1.0 xuống 0.5
    return None
```

**Lưu ý**: Sau khi test xong, đổi lại giá trị mặc định!

## Expected Results

Sau vài phút sử dụng bình thường, bạn sẽ thấy:

```
screenshots/
└── username123/
    └── 2024/
        └── 12/
            └── 22/
                ├── screen_143000.jpg  (FULL frame ban đầu)
                ├── screen_143005.jpg  (Thay đổi lớn - đổi cửa sổ)
                ├── screen_143012.jpg  (Thay đổi lớn - scroll)
                ├── screen_143025.jpg  (Thay đổi lớn - mở app mới)
                ├── screen_143100.jpg  (FULL frame định kỳ)
                └── ...
```

Số lượng screenshots phụ thuộc vào:
- Mức độ hoạt động của user
- Ngưỡng thay đổi (change_threshold)
- Throttling (3 giây/lần)

## Troubleshooting

### Không thấy screenshot nào?

1. ✅ Kiểm tra client đã đăng nhập chưa
2. ✅ Kiểm tra manager đã kết nối chưa (để kích hoạt screen sharing)
3. ✅ Xem logs của server
4. ✅ Kiểm tra quyền ghi vào thư mục `screenshots/`

### Chỉ có 1 screenshot?

- Đợi thêm 1-2 phút và thực hiện các thao tác lớn (scroll, đổi tab, mở app)
- Client chỉ gửi FULL frame mỗi 60 giây
- RECT frames chỉ được lưu khi thay đổi > ngưỡng

### Quá nhiều screenshots?

- Tăng `change_threshold` lên (ví dụ: 100,000 hoặc 200,000)
- Tăng throttling time trong `_save_image` (ví dụ: 5 hoặc 10 giây)

## Làm Sạch Sau Test

```bash
# Xóa tất cả screenshots
rm -rf screenshots

# Hoặc trên Windows
rd /s /q screenshots
```

## Performance Check

Kiểm tra hiệu năng:

1. **CPU Usage**: Server không tăng đáng kể khi lưu screenshots
2. **Memory**: Base images được cache, chiếm ~5-10MB/client
3. **Disk I/O**: Mỗi screenshot ~300-500KB, ghi không đồng bộ
4. **Latency**: Không ảnh hưởng tới streaming (non-blocking)

## Next Steps

Sau khi test thành công:
1. Điều chỉnh `change_threshold` phù hợp với use case
2. Thiết lập cleanup tự động (xem `SCREENSHOT_STORAGE_README.md`)
3. Cấu hình backup định kỳ
4. Thiết lập monitoring cho dung lượng disk
