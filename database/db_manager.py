import mysql.connector
import pandas as pd

# Cấu hình kết nối
config = {
    "host": "localhost",
    "user": "root",
    "password": "085213",
    "database": "pbl4",
    "port": 3306
}

# Kết nối MySQL
conn = mysql.connector.connect(**config)

# Đọc dữ liệu vào DataFrame
query = "SELECT * FROM session"
df = pd.read_sql(query, conn)

# Hiển thị
print(df)

# Đóng kết nối
conn.close()
