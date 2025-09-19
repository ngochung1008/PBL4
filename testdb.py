import mysql.connector

# Kết nối đến MySQL
conn = mysql.connector.connect(
    host="localhost",       # Địa chỉ server MySQL (vd: "127.0.0.1")
    user="root",            # Tài khoản MySQL
    password="root",# Mật khẩu MySQL
    database="pbl4"       # Tên database muốn dùng
)

cursor1 = conn.cursor()
cursor1.execute("SELECT DATABASE()")
print("Đang kết nối tới database:", cursor1.fetchone())

cursor2 = conn.cursor()
cursor2.execute("SHOW TABLES")
for table in cursor2.fetchall():
    print(table[0])

# Đóng kết nối
cursor1.close()
cursor2.close()
conn.close()
