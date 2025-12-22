"""
Quick Test Script - Test File Transfer Functionality
Kiểm tra nhanh chức năng truyền file
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def test_database_connection():
    """Test kết nối database"""
    print("\n" + "="*50)
    print("TEST 1: Database Connection")
    print("="*50)
    
    try:
        from config import server_config
        import mysql.connector
        
        conn = mysql.connector.connect(
            host=server_config.host_db,
            user=server_config.user_db,
            password=server_config.password_db,
            database=server_config.database_db
        )
        
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        print("✅ Database connection successful!")
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def test_table_exists():
    """Test xem bảng file_transfers đã tồn tại chưa"""
    print("\n" + "="*50)
    print("TEST 2: Check file_transfers Table")
    print("="*50)
    
    try:
        from config import server_config
        import mysql.connector
        
        conn = mysql.connector.connect(
            host=server_config.host_db,
            user=server_config.user_db,
            password=server_config.password_db,
            database=server_config.database_db
        )
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_schema = %s 
            AND table_name = 'file_transfers'
        """, (server_config.database_db,))
        
        count = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        if count > 0:
            print("✅ Table 'file_transfers' exists!")
            return True
        else:
            print("⚠️ Table 'file_transfers' does not exist.")
            print("   Run: python run_migrations.py")
            return False
            
    except Exception as e:
        print(f"❌ Error checking table: {e}")
        return False

def test_file_transfer_manager():
    """Test FileTransferManager"""
    print("\n" + "="*50)
    print("TEST 3: FileTransferManager")
    print("="*50)
    
    try:
        from src.server.core.file_transfer_manager import FileTransferManager
        
        ftm = FileTransferManager()
        
        # Test create transfer record
        transfer_id = ftm.create_transfer_record(
            sender_id="test_client",
            sender_type="client",
            receiver_id="test_manager",
            receiver_type="manager",
            filename="test_file.txt",
            filesize=1024,
            file_hash="abc123"
        )
        
        if transfer_id:
            print(f"✅ Created transfer record #{transfer_id}")
            
            # Test update status
            ftm.update_transfer_status(transfer_id, "completed")
            print(f"✅ Updated status to 'completed'")
            
            # Test get history
            history = ftm.get_transfer_history("test_client", "client", 10)
            print(f"✅ Retrieved {len(history)} transfer records")
            
            return True
        else:
            print("❌ Failed to create transfer record")
            return False
            
    except Exception as e:
        print(f"❌ FileTransferManager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_imports():
    """Test tất cả imports"""
    print("\n" + "="*50)
    print("TEST 4: Module Imports")
    print("="*50)
    
    modules_to_test = [
        ("Server FileTransferManager", "src.server.core.file_transfer_manager", "FileTransferManager"),
        ("Server FileTransferHandler", "src.server.core.file_transfer_handler", "FileTransferHandler"),
        ("Client FileTransfer", "src.client.client_file_transfer", "ClientFileTransfer"),
        ("Manager FileTransfer", "src.manager.manager_file_transfer", "ManagerFileTransfer"),
    ]
    
    all_passed = True
    
    for name, module_path, class_name in modules_to_test:
        try:
            module = __import__(module_path, fromlist=[class_name])
            cls = getattr(module, class_name)
            print(f"✅ {name}: OK")
        except Exception as e:
            print(f"❌ {name}: FAILED - {e}")
            all_passed = False
    
    return all_passed

def test_constants():
    """Test file transfer constants"""
    print("\n" + "="*50)
    print("TEST 5: File Transfer Constants")
    print("="*50)
    
    try:
        from src.server.server_constants import (
            CMD_SEND_FILE, 
            CMD_FILE_TRANSFER_START,
            CMD_FILE_TRANSFER_ACK,
            CMD_FILE_TRANSFER_COMPLETE,
            CMD_FILE_TRANSFER_ERROR,
            CHANNEL_FILE
        )
        
        print(f"✅ CMD_SEND_FILE: {CMD_SEND_FILE}")
        print(f"✅ CMD_FILE_TRANSFER_START: {CMD_FILE_TRANSFER_START}")
        print(f"✅ CMD_FILE_TRANSFER_ACK: {CMD_FILE_TRANSFER_ACK}")
        print(f"✅ CMD_FILE_TRANSFER_COMPLETE: {CMD_FILE_TRANSFER_COMPLETE}")
        print(f"✅ CMD_FILE_TRANSFER_ERROR: {CMD_FILE_TRANSFER_ERROR}")
        print(f"✅ CHANNEL_FILE: {CHANNEL_FILE}")
        
        return True
        
    except Exception as e:
        print(f"❌ Constants test failed: {e}")
        return False

def main():
    """Chạy tất cả tests"""
    print("\n" + "="*60)
    print("FILE TRANSFER FUNCTIONALITY TEST SUITE")
    print("="*60)
    
    results = []
    
    # Test 1: Database connection
    results.append(("Database Connection", test_database_connection()))
    
    # Test 2: Table exists
    results.append(("Table Exists", test_table_exists()))
    
    # Test 3: Imports
    results.append(("Module Imports", test_imports()))
    
    # Test 4: Constants
    results.append(("Constants", test_constants()))
    
    # Test 5: FileTransferManager (only if table exists)
    if results[1][1]:  # If table exists
        results.append(("FileTransferManager", test_file_transfer_manager()))
    else:
        results.append(("FileTransferManager", None))
        print("\n⚠️ Skipping FileTransferManager test (table doesn't exist)")
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = 0
    failed = 0
    skipped = 0
    
    for test_name, result in results:
        if result is True:
            print(f"✅ {test_name}: PASSED")
            passed += 1
        elif result is False:
            print(f"❌ {test_name}: FAILED")
            failed += 1
        else:
            print(f"⚠️ {test_name}: SKIPPED")
            skipped += 1
    
    print("\n" + "="*60)
    print(f"Total: {len(results)} tests")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Skipped: {skipped}")
    print("="*60)
    
    if failed > 0:
        print("\n❌ Some tests failed!")
        print("\nRecommendations:")
        if not results[1][1]:  # Table doesn't exist
            print("  1. Run: python run_migrations.py")
        print("  2. Check config/server_config.py for correct database settings")
        print("  3. Ensure MySQL server is running")
        return False
    elif skipped > 0:
        print("\n⚠️ Some tests were skipped. Run migrations first.")
        return False
    else:
        print("\n✅ All tests passed!")
        print("\nFile transfer functionality is ready to use!")
        return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
