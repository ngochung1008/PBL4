import mysql.connector
from config import server_config

class Database:
    def __init__(self):
        self.conn = mysql.connector.connect(
            host=server_config.host_db,
            user=server_config.user_db,
            password=server_config.password_db,
            database=server_config.database_db
        )
        self.cursor = self.conn.cursor()

    def log_transfer(self, filename, filesize, direction):
        sql = """
            INSERT INTO filetransfers 
            (ViewID, FileName, FilePath, FileSize, Direction)
            VALUES (NULL, %s, NULL, %s, %s)
        """
        self.cursor.execute(sql, (filename, filesize, direction))
        self.conn.commit()

    def close(self):
        self.cursor.close()
        self.conn.close()
