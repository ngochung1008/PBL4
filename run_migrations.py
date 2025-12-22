"""
Run database migrations - Chạy các migration SQL
"""

import mysql.connector
import os
from config import server_config

def run_migrations():
    """Chạy tất cả các migration files trong thư mục migrations"""
    
    # Kết nối database
    try:
        conn = mysql.connector.connect(
            host=server_config.host_db,
            user=server_config.user_db,
            password=server_config.password_db,
            database=server_config.database_db
        )
        cursor = conn.cursor()
        print(f"✅ Đã kết nối database: {server_config.database_db}")
    except Exception as e:
        print(f"❌ Lỗi kết nối database: {e}")
        return False
    
    # Đọc và chạy migration files
    migrations_dir = "migrations"
    if not os.path.exists(migrations_dir):
        print(f"❌ Thư mục {migrations_dir} không tồn tại")
        return False
    
    migration_files = sorted([f for f in os.listdir(migrations_dir) if f.endswith('.sql')])
    
    if not migration_files:
        print("⚠️ Không tìm thấy migration files")
        return True
    
    print(f"\nTìm thấy {len(migration_files)} migration files:")
    for f in migration_files:
        print(f"  - {f}")
    
    print("\n" + "="*50)
    
    # Chạy từng migration
    for migration_file in migration_files:
        filepath = os.path.join(migrations_dir, migration_file)
        
        try:
            print(f"\n📝 Đang chạy: {migration_file}")
            
            with open(filepath, 'r', encoding='utf-8') as f:
                sql = f.read()
            
            # Thực thi SQL
            cursor.execute(sql)
            conn.commit()
            
            print(f"✅ Hoàn thành: {migration_file}")
            
        except mysql.connector.Error as e:
            # Bỏ qua lỗi "table already exists"
            if "already exists" in str(e).lower():
                print(f"⚠️ Bảng đã tồn tại (bỏ qua): {migration_file}")
            else:
                print(f"❌ Lỗi khi chạy {migration_file}: {e}")
                conn.rollback()
        except Exception as e:
            print(f"❌ Lỗi: {e}")
            conn.rollback()
    
    # Đóng kết nối
    cursor.close()
    conn.close()
    
    print("\n" + "="*50)
    print("✅ Hoàn thành tất cả migrations!")
    return True


if __name__ == "__main__":
    print("="*50)
    print("DATABASE MIGRATION TOOL")
    print("="*50)
    
    success = run_migrations()
    
    if success:
        print("\n✅ Migration thành công!")
    else:
        print("\n❌ Migration thất bại!")
        exit(1)
