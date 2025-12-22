"""
View Screenshots Tool
Công cụ xem và quản lý screenshots đã lưu
"""

import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# Thêm thư mục gốc vào sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.server.core.screenshot_storage import ScreenshotStorage


def format_file_size(size_bytes):
    """Format file size to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


def list_all_clients(storage):
    """Liệt kê tất cả clients"""
    print("=" * 80)
    print("ALL CLIENTS WITH SCREENSHOTS")
    print("=" * 80)
    
    clients = storage.get_all_client_names()
    
    if not clients:
        print("No clients found with screenshots.")
        return
    
    print(f"\nTotal: {len(clients)} client(s)\n")
    
    for i, client in enumerate(clients, 1):
        screenshots_today = storage.get_client_screenshots(client)
        print(f"{i}. {client} - {len(screenshots_today)} screenshot(s) today")
    
    print("\n" + "=" * 80)


def view_client_screenshots(storage, client_name, date=None):
    """Xem screenshots của một client"""
    if date is None:
        date = datetime.now()
        date_str = "Today"
    else:
        date_str = date.strftime("%Y-%m-%d")
    
    print("=" * 80)
    print(f"SCREENSHOTS FOR: {client_name} ({date_str})")
    print("=" * 80)
    
    screenshots = storage.get_client_screenshots(client_name, date)
    
    if not screenshots:
        print(f"\nNo screenshots found for {client_name} on {date_str}")
        return
    
    print(f"\nTotal: {len(screenshots)} screenshot(s)\n")
    
    total_size = 0
    for i, filepath in enumerate(screenshots, 1):
        path = Path(filepath)
        if path.exists():
            size = path.stat().st_size
            total_size += size
            timestamp = path.name.replace("screen_", "").replace(".jpg", "")
            print(f"{i}. {path.name}")
            print(f"   Size: {format_file_size(size)}")
            print(f"   Path: {filepath}")
            print()
    
    print(f"Total Size: {format_file_size(total_size)}")
    print("=" * 80)


def interactive_mode(storage):
    """Chế độ tương tác"""
    while True:
        print("\n" + "=" * 80)
        print("SCREENSHOT VIEWER - INTERACTIVE MODE")
        print("=" * 80)
        print("\nOptions:")
        print("  1. List all clients")
        print("  2. View client screenshots (today)")
        print("  3. View client screenshots (specific date)")
        print("  4. Search screenshots")
        print("  5. Storage statistics")
        print("  0. Exit")
        print()
        
        choice = input("Enter your choice: ").strip()
        
        if choice == "0":
            print("Goodbye!")
            break
        
        elif choice == "1":
            list_all_clients(storage)
        
        elif choice == "2":
            client_name = input("Enter client username: ").strip()
            if client_name:
                view_client_screenshots(storage, client_name)
            else:
                print("ERROR: Client name cannot be empty")
        
        elif choice == "3":
            client_name = input("Enter client username: ").strip()
            date_str = input("Enter date (YYYY-MM-DD): ").strip()
            
            if not client_name:
                print("ERROR: Client name cannot be empty")
                continue
            
            try:
                date = datetime.strptime(date_str, "%Y-%m-%d")
                view_client_screenshots(storage, client_name, date)
            except ValueError:
                print(f"ERROR: Invalid date format '{date_str}'. Use YYYY-MM-DD")
        
        elif choice == "4":
            search_screenshots(storage)
        
        elif choice == "5":
            show_statistics(storage)
        
        else:
            print("ERROR: Invalid choice")


def search_screenshots(storage):
    """Tìm kiếm screenshots"""
    print("\n" + "=" * 80)
    print("SEARCH SCREENSHOTS")
    print("=" * 80)
    
    client_name = input("\nEnter client username (or * for all): ").strip()
    
    if client_name == "*":
        clients = storage.get_all_client_names()
    else:
        clients = [client_name]
    
    # Nhập khoảng thời gian
    print("\nTime range:")
    print("  1. Today")
    print("  2. Last 7 days")
    print("  3. Last 30 days")
    print("  4. Custom range")
    
    range_choice = input("Select time range: ").strip()
    
    if range_choice == "1":
        dates = [datetime.now()]
    elif range_choice == "2":
        dates = [datetime.now() - timedelta(days=i) for i in range(7)]
    elif range_choice == "3":
        dates = [datetime.now() - timedelta(days=i) for i in range(30)]
    elif range_choice == "4":
        start_str = input("Start date (YYYY-MM-DD): ").strip()
        end_str = input("End date (YYYY-MM-DD): ").strip()
        try:
            start_date = datetime.strptime(start_str, "%Y-%m-%d")
            end_date = datetime.strptime(end_str, "%Y-%m-%d")
            dates = []
            current = start_date
            while current <= end_date:
                dates.append(current)
                current += timedelta(days=1)
        except ValueError:
            print("ERROR: Invalid date format")
            return
    else:
        print("ERROR: Invalid choice")
        return
    
    # Tìm kiếm
    print(f"\nSearching {len(clients)} client(s) across {len(dates)} day(s)...\n")
    
    total_found = 0
    total_size = 0
    
    for client in clients:
        client_screenshots = []
        for date in dates:
            screenshots = storage.get_client_screenshots(client, date)
            client_screenshots.extend(screenshots)
        
        if client_screenshots:
            print(f"\n{client}: {len(client_screenshots)} screenshot(s)")
            
            client_size = 0
            for filepath in client_screenshots:
                path = Path(filepath)
                if path.exists():
                    size = path.stat().st_size
                    client_size += size
            
            print(f"  Total Size: {format_file_size(client_size)}")
            total_size += client_size
            total_found += len(client_screenshots)
    
    print("\n" + "=" * 80)
    print(f"Search Results: {total_found} screenshot(s), {format_file_size(total_size)}")
    print("=" * 80)


def show_statistics(storage):
    """Hiển thị thống kê"""
    print("\n" + "=" * 80)
    print("STORAGE STATISTICS")
    print("=" * 80)
    
    base_path = Path(storage.base_path)
    
    if not base_path.exists():
        print("\nNo screenshot storage directory found.")
        return
    
    # Tính tổng số file và dung lượng
    total_files = 0
    total_size = 0
    
    for filepath in base_path.rglob("*.jpg"):
        total_files += 1
        total_size += filepath.stat().st_size
    
    # Số lượng clients
    clients = storage.get_all_client_names()
    
    print(f"\nBase Path: {base_path.absolute()}")
    print(f"Total Clients: {len(clients)}")
    print(f"Total Screenshots: {total_files}")
    print(f"Total Size: {format_file_size(total_size)}")
    
    if total_files > 0:
        print(f"Average Size: {format_file_size(total_size / total_files)}")
    
    # Top 5 clients theo số lượng screenshots
    print("\n" + "-" * 80)
    print("TOP 5 CLIENTS BY SCREENSHOT COUNT (Today)")
    print("-" * 80)
    
    client_counts = []
    for client in clients:
        screenshots = storage.get_client_screenshots(client)
        if screenshots:
            client_counts.append((client, len(screenshots)))
    
    client_counts.sort(key=lambda x: x[1], reverse=True)
    
    for i, (client, count) in enumerate(client_counts[:5], 1):
        print(f"{i}. {client}: {count} screenshot(s)")
    
    print("\n" + "=" * 80)


def main():
    """Main function"""
    storage = ScreenshotStorage(base_path="screenshots")
    
    if len(sys.argv) == 1:
        # Interactive mode
        interactive_mode(storage)
    
    elif len(sys.argv) == 2:
        command = sys.argv[1]
        
        if command == "list":
            list_all_clients(storage)
        
        elif command == "stats":
            show_statistics(storage)
        
        else:
            # View specific client
            view_client_screenshots(storage, command)
    
    elif len(sys.argv) == 3:
        client_name = sys.argv[1]
        date_str = sys.argv[2]
        
        try:
            date = datetime.strptime(date_str, "%Y-%m-%d")
            view_client_screenshots(storage, client_name, date)
        except ValueError:
            print(f"ERROR: Invalid date format '{date_str}'. Use YYYY-MM-DD")
            sys.exit(1)
    
    else:
        print("Usage:")
        print("  python view_screenshots.py                    # Interactive mode")
        print("  python view_screenshots.py list               # List all clients")
        print("  python view_screenshots.py stats              # Show statistics")
        print("  python view_screenshots.py <client_name>      # View client screenshots (today)")
        print("  python view_screenshots.py <client_name> <date>  # View client screenshots (specific date)")
        print("\nExample:")
        print("  python view_screenshots.py john")
        print("  python view_screenshots.py john 2024-12-22")


if __name__ == "__main__":
    main()
