import socket
import threading
import mysql.connector
import json
import uuid
from datetime import datetime

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="085213",     
        database="pbl4"      
    )

def login_user(username, password, client_ip):
    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        cursor.execute("SELECT * FROM users WHERE Username = %s", (username,))
        user = cursor.fetchone()

        if not user:
            return {"status": "error", "error": "Tài khoản không tồn tại."}

        if password != user["PasswordHash"]:
            return {"status": "error", "error": "Sai mật khẩu."}

        session_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO session (SessionID, UserID, Ip, StartTime)
            VALUES (%s, %s, %s, %s)
        """, (session_id, user["UserID"], client_ip, datetime.now()))

        cursor.execute("UPDATE users SET LastLogin = NOW() WHERE UserID = %s", (user["UserID"],))
        db.commit()

        def safe_datetime(value):
            if isinstance(value, datetime):
                return value.strftime("%Y-%m-%d %H:%M:%S")
            return value or ""

        return {
            "status": "ok",
            "token": session_id,
            "user": {
                "UserID": user["UserID"],
                "Username": user["Username"],
                "FullName": user.get("FullName", ""),
                "Email": user.get("Email", ""),
                "CreatedAt": safe_datetime(user.get("CreatedAt")),
                "LastLogin": safe_datetime(user.get("LastLogin")),
                "Role": user["Role"],
            }
    }

    except Exception as e:
        return {"status": "error", "error": str(e)}

    finally:
        db.close()

def handle_client(conn, addr):
    client_ip = addr[0]
    print(f"Client connected from {client_ip}")

    try:
        while True:
            data = conn.recv(4096)
            if not data:
                break

            msg = json.loads(data.decode("utf-8"))
            action = msg.get("action")

            if action == "login":
                username = msg.get("username")
                password = msg.get("password")
                result = login_user(username, password, client_ip)
                conn.sendall(json.dumps(result).encode("utf-8"))
            else:
                conn.sendall(json.dumps({"status": "error", "error": "Unknown action"}).encode("utf-8"))

    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()
        print(f"🔌 Client disconnected: {client_ip}")


def start_server():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("0.0.0.0", 5000))
    s.listen(5)
    print("Chat server running at 0.0.0.0:5000")

    while True:
        conn, addr = s.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    start_server()
