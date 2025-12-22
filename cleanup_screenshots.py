"""
Cleanup Old Screenshots Script
Tự động xóa screenshots cũ hơn N ngày
"""

import sys
import os
from datetime import datetime

# Thêm thư mục gốc vào sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.server.core.screenshot_storage import ScreenshotStorage


def main():
    """Main cleanup function"""
    print("=" * 60)
    print("Screenshot Cleanup Tool")
    print("=" * 60)
    
    # Khởi tạo storage
    storage = ScreenshotStorage(base_path="screenshots")
    
    # Lấy số ngày từ command line hoặc dùng mặc định
    if len(sys.argv) > 1:
        try:
            retention_days = int(sys.argv[1])
        except ValueError:
            print(f"ERROR: Invalid days value '{sys.argv[1]}'. Using default 30 days.")
            retention_days = 30
    else:
        retention_days = 30
    
    print(f"\nRetention Period: {retention_days} days")
    print(f"Cleaning up screenshots older than {retention_days} days...\n")
    
    # Chạy cleanup
    try:
        storage.cleanup_old_screenshots(days=retention_days)
        print("\n✓ Cleanup completed successfully")
    except Exception as e:
        print(f"\n✗ Cleanup failed: {e}")
        sys.exit(1)
    
    # Hiển thị thống kê
    print("\n" + "=" * 60)
    print("Storage Statistics")
    print("=" * 60)
    
    clients = storage.get_all_client_names()
    print(f"Total Clients: {len(clients)}")
    
    if clients:
        print("\nClients with screenshots:")
        for client in clients:
            screenshots = storage.get_client_screenshots(client)
            print(f"  - {client}: {len(screenshots)} screenshot(s) today")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
