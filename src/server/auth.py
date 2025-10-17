import mysql.connector
import getpass
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

ph = PasswordHasher(
    time_cost=2,     
    memory_cost=65536, 
    parallelism=2   
)
roles = ['admin', 'user', 'viewer']

def sign_in(username, password):
    conn = mysql.connector.connect(
        host="localhost",       # Địa chỉ server MySQL (vd: "127.0.0.1")
        user="root",            # Tài khoản MySQL
        password="root",# Mật khẩu MySQL
        database="pbl4"       # Tên database muốn dùng
    )
    query = "SELECT * FROM users WHERE Username = %s"
    cursor1 = conn.cursor()
    cursor1.execute(query, (username,))
    row = cursor1.fetchone()
    if row is None:
        cursor1.close()
        conn.close()
        return False
    else:
        stored_hash = row[2]  # Giả sử PasswordHash là cột thứ 3
        cursor1.close()
        try:
            ph.verify(stored_hash, password)
            return True
        except VerifyMismatchError:
            return False
        finally:
            cursor1.close()
            conn.close()
        

def sign_up(username, password, fullname, email):
    conn = mysql.connector.connect(
        host="localhost",       # Địa chỉ server MySQL (vd: "127.0.0.1")
        user="root",            # Tài khoản MySQL
        password="root",# Mật khẩu MySQL
        database="pbl4"       # Tên database muốn dùng
    )
    hashed = ph.hash(password)
    role = roles[1]  # Mặc định role là 'user'
    query = "INSERT INTO users (Username, PasswordHash, Fullname, Email, Role) VALUES (%s, %s, %s, %s, %s)"
    cursor = conn.cursor()
    try:
        cursor.execute(query, (username, hashed, fullname, email, role))
        conn.commit()
        return True
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return False
    finally:
        cursor.close()
        conn.close()

def create_session(user_name, ip, mac_ip):
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="root",
            database="pbl4"
        )
        cursor = conn.cursor()

        # 1. Lấy UserID theo Username
        cursor.execute("SELECT UserID FROM Users WHERE Username = %s", (user_name,))
        result = cursor.fetchone()
        if not result:
            raise ValueError("User không tồn tại")

        user_id = result[0]

        # 2. Insert Session (không cần SessionID, MySQL tự sinh)
        cursor.execute("""
            INSERT INTO Session (UserID, Ip, MacIp)
            VALUES (%s, %s, %s)
        """, (user_id, ip, mac_ip))
        conn.commit()

        # 3. Lấy lại SessionID vừa tạo (lấy record mới nhất của user này)
        cursor.execute("""
            SELECT SessionID FROM Session 
            WHERE UserID = %s 
            ORDER BY StartTime DESC 
            LIMIT 1
        """, (user_id,))
        session_id = cursor.fetchone()[0]

        return session_id

    except Exception as e:
        print("Lỗi:", e)
        return None
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def get_user_by_sessionid(sesion_id):
    print("Fetching user for SessionID:", sesion_id)
    try:
        print("Connecting to DB...")
        conn = mysql.connector.connect(
            host="localhost",       # Địa chỉ server MySQL (vd: "127.0.0.1")
            user="root",            # Tài khoản MySQL
            password="root",# Mật khẩu MySQL
            database="pbl4"       # Tên database muốn dùng
        )
        print("✅ Connected to DB")

        query = "SELECT SessionID FROM Session WHERE SessionID = %s"
        cursor1 = conn.cursor()
        cursor1.execute(query, (sesion_id,))
        result = cursor1.fetchone()
        
        if not result:
            raise ValueError("User không tồn tại")
        
        user_id = result[0]
        print(user_id)
        
        return user_id

    except Exception as e:
        print("Lỗi:", e)
        return None
    finally:
        if conn.is_connected():
            cursor1.close()
            conn.close()

        
# print(sign_in("admin", "admin123"))
# print(sign_up("admin", "admin123", "Administrator", "admin@gmail.com"))