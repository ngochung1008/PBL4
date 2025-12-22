# Debug Screenshot Storage - Hướng Dẫn

## Vấn Đề: "Không lưu ảnh khi đổi tab/màn hình"

### Nguyên nhân có thể:

1. **Ngưỡng quá cao** - Thay đổi không đủ lớn
2. **Throttling** - Lưu quá nhanh (chưa đủ thời gian chờ)
3. **Client không gửi RECT frames** - Kiểm tra logs
4. **Base image chưa được khởi tạo** - Client chưa gửi FULL frame

## Bước 1: Kiểm Tra Logs Server

Chạy server và xem logs:

```bash
python run_server.py
```

### Logs Cần Chú Ý:

#### ✅ Logs Tốt (Screenshot đang hoạt động):

```
[ScreenshotStorage] Initialized with base path: D:\PBL\PBL4\screenshots
[ScreenshotStorage] Change threshold: 20000 pixels

[ScreenshotStorage] Updated base image for username123: 1920x1080
[ScreenshotStorage] ✓ Saved screenshot: screenshots/username123/2024/12/22/screen_143000.jpg

[ScreenshotStorage] RECT for username123: 300x400 at (100,200) = 120000 pixels
[ScreenshotStorage] ✅ Change > threshold (120000 >= 20000), attempting save...
[ScreenshotStorage] Throttle OK: 2.34s since last save
[ScreenshotStorage] ✓ Saved screenshot: screenshots/username123/2024/12/22/screen_143005.jpg
```

#### ⚠️ Logs Cho Thấy Vấn Đề:

**Vấn đề 1: Thay đổi nhỏ hơn ngưỡng**
```
[ScreenshotStorage] RECT for username123: 50x60 at (500,300) = 3000 pixels
[ScreenshotStorage] ❌ Change < threshold (3000 < 20000), skipping save
```
→ **Giải pháp**: Giảm `change_threshold` xuống 5,000

**Vấn đề 2: Throttled (lưu quá nhanh)**
```
[ScreenshotStorage] RECT for username123: 300x400 at (100,200) = 120000 pixels
[ScreenshotStorage] ✅ Change > threshold (120000 >= 20000), attempting save...
[ScreenshotStorage] Throttled: Only 0.45s since last save (need 1.0s)
[ScreenshotStorage] ⚠️ Screenshot not saved (throttled or other reason)
```
→ **Giải pháp**: Đợi thêm 1 giây hoặc giảm throttling

**Vấn đề 3: Không có base image**
```
[ScreenshotStorage] No base image for username123, skipping RECT
```
→ **Giải pháp**: Đợi client gửi FULL frame (mỗi ~60 giây hoặc khi mới kết nối)

## Bước 2: Test Với Logs Chi Tiết

### Quan sát RECT frames:

Khi bạn đổi tab, bạn sẽ thấy:

```
[ScreenshotStorage] RECT for username123: 1920x1080 at (0,0) = 2073600 pixels
[ScreenshotStorage] ✅ Change > threshold (2073600 >= 20000), attempting save...
```

Nếu KHÔNG thấy dòng "RECT for username123" → Client không gửi RECT frames

## Bước 3: Điều Chỉnh Tạm Thời Để Test

### Giảm Ngưỡng Xuống Rất Thấp

Chỉnh sửa [src/server/core/session_manager.py](src/server/core/session_manager.py):

```python
self.screenshot_storage = ScreenshotStorage(
    base_path="screenshots",
    change_threshold=1000  # CỰC KỲ nhạy - mọi thay đổi đều lưu
)
```

### Tắt Throttling

Chỉnh sửa [src/server/core/screenshot_storage.py](src/server/core/screenshot_storage.py):

Trong method `_save_image`:

```python
# Tạm thời comment dòng này để tắt throttling
# if not force:
#     last_save = self.client_last_save_time.get(client_name)
#     if last_save:
#         time_since_last_save = (datetime.now() - last_save).total_seconds()
#         if time_since_last_save < 1.0:
#             print(f"[ScreenshotStorage] Throttled: Only {time_since_last_save:.2f}s since last save (need 1.0s)")
#             return None
```

**LƯU Ý**: Sau khi test xong, BẬT LẠI throttling!

## Bước 4: Test Từng Trường Hợp

### Test 1: FULL Frame
1. Restart server với logs mới
2. Client kết nối lần đầu
3. Kiểm tra log: `Updated base image for username123`
4. Kiểm tra thư mục: Phải có file `screen_HHMMSS.jpg`

### Test 2: RECT Frame - Đổi Tab
1. Đợi client gửi FULL frame xong
2. Đổi tab trong Chrome/Edge
3. Kiểm tra log ngay lập tức:
   ```
   [ScreenshotStorage] RECT for username123: ...
   ```
4. Nếu pixels > 20,000 → Phải lưu

### Test 3: RECT Frame - Scroll
1. Scroll trang web xuống
2. Kiểm tra log:
   ```
   [ScreenshotStorage] RECT for username123: ...
   ```
3. Nếu scroll nhiều (>20,000 pixels) → Phải lưu

## Bước 5: Phân Tích Kết Quả

### Trường hợp 1: Không thấy "RECT for username123"

→ **Client không gửi RECT frames**

**Nguyên nhân**: 
- Client có thể đang ở chế độ idle (không có manager xem)
- Client chưa được kích hoạt screen sharing

**Giải pháp**:
- Đảm bảo manager đã kết nối và xem màn hình client (VIEW hoặc CONTROL)

### Trường hợp 2: Thấy RECT nhưng pixels < 20,000

→ **Thay đổi quá nhỏ**

**Ví dụ**:
```
[ScreenshotStorage] RECT for username123: 50x100 at (200,300) = 5000 pixels
[ScreenshotStorage] ❌ Change < threshold (5000 < 20000), skipping save
```

**Giải pháp**:
- Giảm `change_threshold` xuống 5,000 hoặc 10,000
- Hoặc thực hiện thay đổi lớn hơn (đổi cửa sổ, scroll nhiều)

### Trường hợp 3: Pixels > 20,000 nhưng vẫn không lưu

→ **Bị throttled**

**Ví dụ**:
```
[ScreenshotStorage] Throttled: Only 0.5s since last save (need 1.0s)
```

**Giải pháp**:
- Đợi thêm 1 giây rồi thử lại
- Hoặc giảm throttling time xuống 0.5 giây

## Bước 6: Các Thiết Lập Khuyến Nghị

### Cho Môi Trường Test (Debug)

```python
# session_manager.py
self.screenshot_storage = ScreenshotStorage(
    base_path="screenshots",
    change_threshold=5000  # Rất nhạy
)

# screenshot_storage.py - _save_image()
if time_since_last_save < 0.5:  # 0.5 giây
    return None
```

→ Lưu nhiều ảnh, dễ test

### Cho Môi Trường Production

```python
# session_manager.py
self.screenshot_storage = ScreenshotStorage(
    base_path="screenshots",
    change_threshold=20000  # Cân bằng (mặc định)
)

# screenshot_storage.py - _save_image()
if time_since_last_save < 1.0:  # 1 giây
    return None
```

→ Tiết kiệm dung lượng, capture đủ thông tin

## Bước 7: Timeline Dự Kiến

Với thiết lập mặc định (threshold=20,000, throttle=1s):

```
00:00 - Client kết nối, gửi FULL frame → ✅ Lưu (screen_140000.jpg)
00:03 - Gõ text (3,000 pixels) → ❌ Không lưu (< 20,000)
00:05 - Đổi tab (800,000 pixels) → ✅ Lưu (screen_140005.jpg)
00:06 - Click menu (5,000 pixels) → ❌ Không lưu (< 20,000)
00:08 - Scroll xuống (50,000 pixels) → ✅ Lưu (screen_140008.jpg)
00:09 - Scroll thêm (50,000 pixels) → ❌ Throttled (< 1s)
00:10 - Scroll thêm (50,000 pixels) → ✅ Lưu (screen_140010.jpg)
01:00 - FULL frame định kỳ → ✅ Lưu (screen_140100.jpg)
```

→ Kết quả: 5 screenshots trong 1 phút

## Bước 8: Checklist Debug

- [ ] Server đang chạy với logs đầy đủ
- [ ] Client đã kết nối và authenticated
- [ ] Manager đã kết nối để kích hoạt screen sharing
- [ ] Thấy log "Updated base image" (FULL frame)
- [ ] Thấy log "RECT for username" khi đổi tab
- [ ] Kiểm tra pixels có >= threshold không
- [ ] Kiểm tra có bị throttled không
- [ ] Kiểm tra thư mục screenshots/ có file mới không

## FAQ

**Q: Tại sao chỉ có 3 ảnh ban đầu?**

A: Có thể do:
1. Client chỉ gửi FULL frame ban đầu (3 lần), sau đó gửi toàn RECT nhỏ
2. RECT frames không đủ lớn để lưu (< 20,000 pixels)
3. Bị throttled khi lưu liên tục

**Q: Đổi tab rồi nhưng không lưu?**

A: Kiểm tra logs xem:
1. Client có gửi RECT frame không? (xem log "RECT for...")
2. Pixels có >= 20,000 không?
3. Có bị throttled không? (đợi 1 giây)

**Q: Cần đợi bao lâu sau khi đổi tab?**

A: Với thiết lập mặc định:
- Client ở VIEW mode: ~3 giây/frame
- Throttling: 1 giây
→ Tổng: Đợi ~3-4 giây rồi kiểm tra

**Q: Làm sao để lưu mọi thay đổi?**

A: Giảm threshold xuống 1,000 và throttling xuống 0.5s (nhưng tốn nhiều dung lượng!)

## Liên Hệ

Nếu vẫn có vấn đề sau khi làm theo hướng dẫn này, gửi logs chi tiết để phân tích.
