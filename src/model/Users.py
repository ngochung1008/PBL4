from datetime import datetime
import mysql.connector

class User:
    def __init__(self, UserID, Username, PasswordHash, FullName, Email, CreatedAt, LastLogin, Role):
        self.UserID = UserID
        self.Username = Username
        self.PasswordHash = PasswordHash
        self.FullName = FullName
        self.Email = Email
        self.CreatedAt = CreatedAt
        self.LastLogin = LastLogin
        self.Role = Role

    def __str__(self):
        return f"[{self.Role.upper()}] {self.Username} ({self.Email})"


def get_user_by_id(user_id):
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="root",
            database="pbl4"
        )
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Users WHERE UserID = %s", (user_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if row:
            return User(**row)
        else:
            return None

    except Exception as e:
        print("Database error:", e)
        return None

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
        
        return get_user_by_id(user_id)

    except Exception as e:
        print("Lỗi:", e)
        return None
    finally:
        if conn.is_connected():
            cursor1.close()
            conn.close()
