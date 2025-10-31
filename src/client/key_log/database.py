import mysql.connector
from mysql.connector import Error

def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="085213",
        database="pbl4"
    )

# 🟢 CREATE
def create_keystroke(key_data, window_title, view_id = None):
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
        print("DB Error:", e)
        return False

    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

# 🔵 READ (tất cả)
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
        if cursor: cursor.close()
        if conn: conn.close()

# 🔵 READ (theo ID)
def get_keystroke_by_id(keystroke_id):
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM keystrokes WHERE KeystrokeID = %s", (keystroke_id,))
        row = cursor.fetchone()
        return row
    except Error as e:
        print("❌ Error reading keystroke by ID:", e)
        return None
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# 🟡 UPDATE (chỉ sửa KeyData, WindowTitle, ViewID)
def update_keystroke(keystroke_id, key_data=None, window_title=None, view_id=None):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        query = """
        UPDATE keystrokes
        SET KeyData = COALESCE(%s, KeyData),
            WindowTitle = COALESCE(%s, WindowTitle),
            ViewID = COALESCE(%s, ViewID)
        WHERE KeystrokeID = %s
        """
        cursor.execute(query, (key_data, window_title, view_id, keystroke_id))
        conn.commit()
        print("✅ Keystroke updated successfully.")
        return True
    except Error as e:
        print("❌ Error updating keystroke:", e)
        return False
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# 🔴 DELETE
def delete_keystroke(keystroke_id):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM keystrokes WHERE KeystrokeID = %s", (keystroke_id,))
        conn.commit()
        print("🗑️ Keystroke deleted successfully.")
        return True
    except Error as e:
        print("❌ Error deleting keystroke:", e)
        return False
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

