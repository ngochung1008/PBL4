from datetime import datetime

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

import mysql.connector

def get_user_by_id(user_id):
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="root",
            database="pbl4"
        )
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Users WHERE UserID = %s", (user_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if row:
            return User(**row)
        else:
            return None

    except mysql.connector.Error as e:
        print("Database error:", e)
        return None

def get_user_by_sessionid(sesion_id):
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="root",
            database="pbl4"
        )
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Session WHERE SessionID = %s", (sesion_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if row:
            return get_user_by_sessionid(row['UserID'])
        else:
            return None

    except mysql.connector.Error as e:
        print("Database error:", e)
        return None