# common_network/durable_queue.py

import sqlite3
import threading
import time
from typing import Optional, Tuple

class DurableQueue:
    def __init__(self, db_path="durable_queue.db"):
        self.db_path = db_path
        # check_same_thread=False: chỉ cho phép luồng tạo ra nó được dùng kết nối
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL;") # bật Write-Ahead Logging → tăng concurrency đọc/ghi.
        self.conn.execute("PRAGMA synchronous=NORMAL;") 
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS queue(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task BLOB,
                timestamp REAL
            )
        """)
        self.lock = threading.Lock()

    def push(self, data: bytes) -> None:
        with self.lock:
            self.conn.execute("INSERT INTO queue(task, timestamp) VALUES(?,?)", (data, time.time()))
            self.conn.commit()

    def pop(self) -> Optional[bytes]:
        with self.lock:
            row = self.conn.execute("SELECT id, task FROM queue ORDER BY id LIMIT 1").fetchone()
            if not row:
                return None
            self.conn.execute("DELETE FROM queue WHERE id=?", (row[0],))
            self.conn.commit()
            return row[1]

    def size(self) -> int:
        with self.lock:
            return self.conn.execute("SELECT COUNT(*) FROM queue").fetchone()[0]

    # Lấy (id, task) đầu tiên mà không xóa.
    def peek(self) -> Optional[Tuple[int, bytes]]:
        with self.lock:
            row = self.conn.execute("SELECT id, task FROM queue ORDER BY id LIMIT 1").fetchone()
            if not row:
                return None
            return row[0], row[1] # (id, task_bytes)