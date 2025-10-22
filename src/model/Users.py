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
