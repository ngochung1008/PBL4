CREATE DATABASE pbl4;
USE pbl4;

-- Bảng Users
CREATE TABLE Users (
    UserID VARCHAR(50) PRIMARY KEY,
    Username VARCHAR(100) NOT NULL UNIQUE,
    PasswordHash VARCHAR(255) NOT NULL,
    FullName VARCHAR(255),
    Email VARCHAR(255) UNIQUE,
	CreatedAt TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,    
	LastLogin TIMESTAMP NULL,
    Role ENUM('admin', 'user', 'viewer') NOT NULL
);

-- Bảng Session
CREATE TABLE Session (
    SessionID VARCHAR(50) PRIMARY KEY,
    UserID VARCHAR(50),
    Ip VARCHAR(45),
    MacIp VARCHAR(100),
    StartTime TIMESTAMP NOT null DEFAULT CURRENT_TIMESTAMP,
    EndTime TIMESTAMP NULL,
    FOREIGN KEY (UserID) REFERENCES Users(UserID)
);

-- Bảng View
CREATE TABLE View (
    ViewID VARCHAR(50) PRIMARY KEY,
    SessionClientId VARCHAR(50),
    SessionServerId VARCHAR(50),
    StartTime TIMESTAMP NOT null DEFAULT CURRENT_TIMESTAMP,
    EndTime TIMESTAMP NULL,
    Status ENUM('active', 'ended', 'error') NOT NULL,
    Note TEXT,
    FOREIGN KEY (SessionClientId) REFERENCES Session(SessionID),
    FOREIGN KEY (SessionServerId) REFERENCES Session(SessionID)
);

-- Bảng Keystrokes
CREATE TABLE Keystrokes (
    KeystrokeID VARCHAR(50) PRIMARY KEY,
    ViewID VARCHAR(50),
    KeyData TEXT,
    WindowTitle VARCHAR(255),
    LoggedAt TIMESTAMP NOT null DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ViewID) REFERENCES View(ViewID)
);

-- Bảng Screenshots
CREATE TABLE Screenshots (
    ScreenshotID VARCHAR(50) PRIMARY KEY,
    ViewID VARCHAR(50),
    ImagePath VARCHAR(255),
    Resolution VARCHAR(50),
    CapturedAt TIMESTAMP NOT null DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ViewID) REFERENCES View(ViewID)
);

-- Bảng RemoteControls
CREATE TABLE RemoteControls (
    ControlID VARCHAR(50) PRIMARY KEY,
    ViewID VARCHAR(50),
    ActionType ENUM('mouse', 'keyboard', 'system'),
    ActionData TEXT,
    ExecutedAt TIMESTAMP NOT null DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ViewID) REFERENCES View(ViewID)
);

-- Bảng FileTransfers
CREATE TABLE FileTransfers (
    TransferID VARCHAR(50) PRIMARY KEY,
    ViewID VARCHAR(50),
    FileName VARCHAR(255),
    FilePath VARCHAR(500),
    FileSize BIGINT,
    Direction ENUM('upload', 'download'),
    TransferredAt TIMESTAMP NOT null DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ViewID) REFERENCES View(ViewID)
);