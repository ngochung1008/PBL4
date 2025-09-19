import mysql.connector
import getpass
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

ph = PasswordHasher(
    time_cost=2,      # số vòng lặp (tăng => chậm hơn, an toàn hơn)
    memory_cost=65536, # bộ nhớ (KB) dùng khi hash
    parallelism=2      # số luồng song song
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

# print(sign_in("admin", "admin123"))
# print(sign_up("admin", "admin123", "Administrator", "admin@gmail.com"))