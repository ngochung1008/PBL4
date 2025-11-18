import mysql.connector
from mysql.connector import Error
from config.server_config import host_db, user_db, password_db, database_db


def get_connection():
    """Tạo kết nối tới MySQL"""
    return mysql.connector.connect(
        host=host_db,
        user=user_db,
        password=password_db,
        database=database_db
    )


# 🟢 CREATE – lưu keystroke mới
def create_keystroke(key_data, window_title, view_id=None):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        query = """
        INSERT INTO keystrokes (KeyData, WindowTitle, ViewID, LoggedAt)
        VALUES (%s, %s, %s, NOW())
        """

        cursor.execute(query, (key_data, window_title, view_id))
        conn.commit()
        return True

    except Error as e:
        print("❌ DB Error:", e)
        return False

    finally:
        try:
            cursor.close()
            conn.close()
        except:
            pass


# 🔵 READ – Lấy tất cả
def get_all_keystrokes():
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM keystrokes ORDER BY LoggedAt DESC")
        rows = cursor.fetchall()
        return rows

    except Error as e:
        print("❌ Error reading keystrokes:", e)
        return []

    finally:
        try:
            cursor.close()
            conn.close()
        except:
            pass


# 🔵 READ – Lấy theo ID
def get_keystroke_by_id(keystroke_id):
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM keystrokes WHERE KeystrokeID = %s",
            (keystroke_id,)
        )
        row = cursor.fetchone()
        return row

    except Error as e:
        print("❌ Error reading by ID:", e)
        return None

    finally:
        try:
            cursor.close()
            conn.close()
        except:
            pass


# 🔵 READ – Lấy N phím gần nhất (cho giao diện)
def get_recent_keystrokes(limit=50):
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        query = """
        SELECT * FROM keystrokes
        ORDER BY LoggedAt DESC
        LIMIT %s
        """
        cursor.execute(query, (limit,))
        rows = cursor.fetchall()
        return rows

    except Error as e:
        print("❌ Error reading recent keystrokes:", e)
        return []

    finally:
        try:
            cursor.close()
            conn.close()
        except:
            pass


# 🟡 UPDATE – sửa dòng log
def update_keystroke(keystroke_id, key_data=None, window_title=None, view_id=None):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        query = """
        UPDATE keystrokes
        SET 
            KeyData = COALESCE(%s, KeyData),
            WindowTitle = COALESCE(%s, WindowTitle),
            ViewID = COALESCE(%s, ViewID)
        WHERE KeystrokeID = %s
        """

        cursor.execute(query, (key_data, window_title, view_id, keystroke_id))
        conn.commit()

        return True

    except Error as e:
        print("❌ Error updating keystroke:", e)
        return False

    finally:
        try:
            cursor.close()
            conn.close()
        except:
            pass


# 🔴 DELETE – xóa log
def delete_keystroke(keystroke_id):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM keystrokes WHERE KeystrokeID = %s", (keystroke_id,))
        conn.commit()

        return True

    except Error as e:
        print("❌ Error deleting keystroke:", e)
        return False

    finally:
        try:
            cursor.close()
            conn.close()
        except:
            pass
