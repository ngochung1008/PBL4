-- =====================================================
-- DATABASE SCHEMA CHO HỆ THỐNG GIÁM SÁT - PBL4
-- Database: pbl4
-- MySQL với InnoDB Engine
-- =====================================================

-- Tạo database nếu chưa có
CREATE DATABASE IF NOT EXISTS pbl4 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

USE pbl4;

-- =====================================================
-- 1. BẢNG USERS (Người dùng)
-- Lưu thông tin đăng nhập và profile người dùng
-- =====================================================
CREATE TABLE IF NOT EXISTS Users (
    UserID INT AUTO_INCREMENT PRIMARY KEY,
    Username VARCHAR(100) NOT NULL UNIQUE,
    PasswordHash VARCHAR(255) NOT NULL COMMENT 'Mã hóa bằng Argon2',
    FullName VARCHAR(255) NOT NULL,
    Email VARCHAR(255) NOT NULL,
    CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Thời gian tạo tài khoản',
    LastLogin DATETIME NULL COMMENT 'Lần đăng nhập cuối',
    Role ENUM('admin', 'user', 'viewer') DEFAULT 'user' COMMENT 'Vai trò người dùng',
    
    INDEX idx_username (Username),
    INDEX idx_email (Email),
    INDEX idx_role (Role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Bảng người dùng hệ thống';

-- =====================================================
-- 2. BẢNG SESSION (Phiên đăng nhập)
-- Lưu thông tin các phiên đăng nhập của người dùng
-- =====================================================
CREATE TABLE IF NOT EXISTS Session (
    SessionID INT AUTO_INCREMENT PRIMARY KEY,
    UserID INT NOT NULL COMMENT 'Liên kết với User',
    Ip VARCHAR(45) COMMENT 'Địa chỉ IP của thiết bị',
    MacIp VARCHAR(17) COMMENT 'Địa chỉ MAC',
    StartTime DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Thời gian bắt đầu phiên',
    EndTime DATETIME NULL COMMENT 'Thời gian kết thúc phiên',
    
    INDEX idx_user_id (UserID),
    INDEX idx_start_time (StartTime),
    INDEX idx_user_start (UserID, StartTime),
    
    FOREIGN KEY (UserID) REFERENCES Users(UserID)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Bảng phiên đăng nhập';

-- =====================================================
-- 3. BẢNG VIEW (Phiên giám sát)
-- Lưu thông tin kết nối giữa Manager và Client
-- =====================================================
CREATE TABLE IF NOT EXISTS `View` (
    ViewID CHAR(36) PRIMARY KEY COMMENT 'UUID của phiên View',
    SessionClientId INT NOT NULL COMMENT 'Session của Client bị xem',
    SessionServerId INT NOT NULL COMMENT 'Session của Manager đang xem',
    Status ENUM('active', 'accepted', 'ended', 'rejected') DEFAULT 'active' COMMENT 'Trạng thái kết nối',
    StartTime DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Thời gian bắt đầu view',
    EndTime DATETIME NULL COMMENT 'Thời gian kết thúc view',
    
    INDEX idx_session_client (SessionClientId),
    INDEX idx_session_server (SessionServerId),
    INDEX idx_status (Status),
    INDEX idx_start_time (StartTime),
    INDEX idx_client_server (SessionClientId, SessionServerId),
    
    FOREIGN KEY (SessionClientId) REFERENCES Session(SessionID)
        ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (SessionServerId) REFERENCES Session(SessionID)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Bảng phiên giám sát (Manager xem Client)';

-- =====================================================
-- 4. BẢNG KEYSTROKES (Keylogger)
-- Lưu lịch sử các phím nhấn trong phiên xem
-- =====================================================
CREATE TABLE IF NOT EXISTS keystrokes (
    KeystrokeID CHAR(36) PRIMARY KEY,
    ViewID CHAR(36) NOT NULL COMMENT 'Liên kết với phiên View',
    KeyData TEXT NOT NULL COMMENT 'Dữ liệu phím nhấn (có thể mã hóa)',
    WindowTitle VARCHAR(500) COMMENT 'Tiêu đề cửa sổ khi nhấn phím',
    ProcessName VARCHAR(255) COMMENT 'Tên tiến trình',
    LoggedAt DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Thời gian ghi log',
    
    INDEX idx_view_id (ViewID),
    INDEX idx_logged_at (LoggedAt),
    INDEX idx_view_logged (ViewID, LoggedAt),
    INDEX idx_process (ProcessName),
    
    FOREIGN KEY (ViewID) REFERENCES `View`(ViewID)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Lưu lịch sử phím nhấn (Keylogger)';

-- =====================================================
-- 5. BẢNG WINDOW LOGS
-- Lưu lịch sử các cửa sổ được mở/focus trong phiên xem
-- =====================================================
CREATE TABLE IF NOT EXISTS window_logs (
    WindowLogID CHAR(36) PRIMARY KEY,
    ViewID CHAR(36) NOT NULL COMMENT 'Liên kết với phiên View',
    WindowTitle VARCHAR(500) NOT NULL COMMENT 'Tiêu đề cửa sổ',
    ProcessName VARCHAR(255) NOT NULL COMMENT 'Tên tiến trình',
    LoggedAt DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Thời gian ghi log',
    
    INDEX idx_view_id (ViewID),
    INDEX idx_logged_at (LoggedAt),
    INDEX idx_view_logged (ViewID, LoggedAt),
    INDEX idx_process (ProcessName),
    
    FOREIGN KEY (ViewID) REFERENCES `View`(ViewID)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Lưu lịch sử cửa sổ';

-- =====================================================
-- 6. BẢNG SCREEN CAPTURES (Screenshots)
-- Lưu thông tin các ảnh chụp màn hình trong phiên xem
-- =====================================================
CREATE TABLE IF NOT EXISTS screen_captures (
    CaptureID CHAR(36) PRIMARY KEY,
    ViewID CHAR(36) NOT NULL COMMENT 'Liên kết với phiên View',
    FilePath VARCHAR(500) NOT NULL COMMENT 'Đường dẫn file ảnh trên server',
    FileName VARCHAR(255) NOT NULL COMMENT 'Tên file ảnh',
    FileSize BIGINT DEFAULT 0 COMMENT 'Kích thước file (bytes)',
    Width INT COMMENT 'Chiều rộng ảnh (pixels)',
    Height INT COMMENT 'Chiều cao ảnh (pixels)',
    CaptureType ENUM('auto', 'manual', 'alert') DEFAULT 'auto' COMMENT 'Loại chụp: tự động/thủ công/cảnh báo',
    CapturedAt DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Thời gian chụp',
    
    INDEX idx_view_id (ViewID),
    INDEX idx_captured_at (CapturedAt),
    INDEX idx_view_captured (ViewID, CapturedAt),
    
    FOREIGN KEY (ViewID) REFERENCES `View`(ViewID)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Lưu thông tin ảnh chụp màn hình';

-- =====================================================
-- 7. BẢNG CONTROL SESSIONS (Phiên điều khiển)
-- Lưu lịch sử các phiên điều khiển (keyboard/mouse control)
-- =====================================================
CREATE TABLE IF NOT EXISTS control_sessions (
    ControlID CHAR(36) PRIMARY KEY,
    ViewID CHAR(36) NOT NULL COMMENT 'Liên kết với phiên View',
    ControlType ENUM('keyboard', 'mouse', 'both') NOT NULL COMMENT 'Loại điều khiển',
    StartTime DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Thời gian bắt đầu điều khiển',
    EndTime DATETIME NULL COMMENT 'Thời gian kết thúc điều khiển',
    InputCount INT DEFAULT 0 COMMENT 'Số lượng input đã gửi',
    Notes TEXT COMMENT 'Ghi chú',
    
    INDEX idx_view_id (ViewID),
    INDEX idx_start_time (StartTime),
    
    FOREIGN KEY (ViewID) REFERENCES `View`(ViewID)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Lưu lịch sử phiên điều khiển';

-- =====================================================
-- 8. BẢNG CONTROL INPUTS (Chi tiết điều khiển)
-- Lưu chi tiết các input trong phiên điều khiển
-- =====================================================
CREATE TABLE IF NOT EXISTS control_inputs (
    InputID CHAR(36) PRIMARY KEY,
    ControlID CHAR(36) NOT NULL COMMENT 'Liên kết với phiên Control',
    InputType ENUM('key_press', 'key_release', 'mouse_click', 'mouse_move', 'mouse_scroll') NOT NULL COMMENT 'Loại input',
    InputData VARCHAR(255) COMMENT 'Dữ liệu input (key code, tọa độ, etc.)',
    PositionX INT COMMENT 'Tọa độ X (cho mouse)',
    PositionY INT COMMENT 'Tọa độ Y (cho mouse)',
    InputAt DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Thời gian input',
    
    INDEX idx_control_id (ControlID),
    INDEX idx_input_at (InputAt),
    
    FOREIGN KEY (ControlID) REFERENCES control_sessions(ControlID)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Lưu chi tiết input trong phiên điều khiển';

-- =====================================================
-- 9. BẢNG FILE TRANSFERS
-- Lưu lịch sử truyền file trong phiên xem
-- =====================================================
CREATE TABLE IF NOT EXISTS file_transfers (
    TransferID CHAR(36) PRIMARY KEY,
    ViewID CHAR(36) NOT NULL COMMENT 'Liên kết với phiên View',
    FileName VARCHAR(255) NOT NULL COMMENT 'Tên file',
    FilePath VARCHAR(500) COMMENT 'Đường dẫn file gốc',
    FileSize BIGINT DEFAULT 0 COMMENT 'Kích thước file (bytes)',
    FileHash VARCHAR(64) COMMENT 'Hash SHA256 của file',
    Direction ENUM('manager_to_client', 'client_to_manager') NOT NULL COMMENT 'Hướng truyền',
    Status ENUM('pending', 'transferring', 'completed', 'failed', 'cancelled') DEFAULT 'pending' COMMENT 'Trạng thái',
    CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Thời gian tạo record',
    
    INDEX idx_view_id (ViewID),
    INDEX idx_view_created (ViewID, CreatedAt),
    INDEX idx_status (Status),
    
    FOREIGN KEY (ViewID) REFERENCES `View`(ViewID)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Lưu lịch sử truyền file';

-- =====================================================
-- 10. BẢNG SECURITY ALERTS (Cảnh báo bảo mật)
-- Lưu các cảnh báo phát hiện trong phiên xem
-- =====================================================
CREATE TABLE IF NOT EXISTS security_alerts (
    AlertID CHAR(36) PRIMARY KEY,
    ViewID CHAR(36) NOT NULL COMMENT 'Liên kết với phiên View',
    AlertType ENUM('suspicious_app', 'keyword_detected', 'unusual_activity', 'file_access', 'other') NOT NULL COMMENT 'Loại cảnh báo',
    Severity ENUM('low', 'medium', 'high', 'critical') DEFAULT 'medium' COMMENT 'Mức độ nghiêm trọng',
    Title VARCHAR(255) NOT NULL COMMENT 'Tiêu đề cảnh báo',
    Description TEXT COMMENT 'Mô tả chi tiết',
    IsAcknowledged BOOLEAN DEFAULT FALSE COMMENT 'Đã xác nhận',
    CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Thời gian tạo',
    
    INDEX idx_view_id (ViewID),
    INDEX idx_view_created (ViewID, CreatedAt),
    INDEX idx_alert_type (AlertType),
    INDEX idx_severity (Severity),
    
    FOREIGN KEY (ViewID) REFERENCES `View`(ViewID)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Lưu cảnh báo bảo mật';

-- =====================================================
-- VIEWS (Truy vấn nhanh)
-- =====================================================

-- View: Thống kê hoạt động theo phiên
CREATE OR REPLACE VIEW view_session_statistics AS
SELECT 
    v.ViewID,
    v.SessionClientId,
    v.SessionServerId,
    v.Status,
    v.StartTime,
    v.EndTime,
    TIMESTAMPDIFF(MINUTE, v.StartTime, COALESCE(v.EndTime, NOW())) AS DurationMinutes,
    (SELECT COUNT(*) FROM keystrokes k WHERE k.ViewID = v.ViewID) AS KeystrokeCount,
    (SELECT COUNT(*) FROM window_logs w WHERE w.ViewID = v.ViewID) AS WindowLogCount,
    (SELECT COUNT(*) FROM screen_captures s WHERE s.ViewID = v.ViewID) AS ScreenCaptureCount,
    (SELECT COUNT(*) FROM control_sessions c WHERE c.ViewID = v.ViewID) AS ControlSessionCount,
    (SELECT COUNT(*) FROM file_transfers f WHERE f.ViewID = v.ViewID) AS FileTransferCount,
    (SELECT COUNT(*) FROM security_alerts a WHERE a.ViewID = v.ViewID) AS AlertCount
FROM `View` v;

-- View: Danh sách user với session gần nhất
CREATE OR REPLACE VIEW view_user_sessions AS
SELECT 
    u.UserID,
    u.Username,
    u.FullName,
    u.Email,
    u.Role,
    u.LastLogin,
    s.SessionID,
    s.Ip,
    s.MacIp,
    s.StartTime AS SessionStart,
    s.EndTime AS SessionEnd
FROM Users u
LEFT JOIN Session s ON u.UserID = s.UserID
ORDER BY u.UserID, s.StartTime DESC;

-- =====================================================
-- STORED PROCEDURES (Tiện ích)
-- =====================================================

-- Procedure: Lấy tổng quan phiên theo ViewID
DELIMITER //
CREATE PROCEDURE IF NOT EXISTS GetViewSummary(IN p_view_id CHAR(36))
BEGIN
    SELECT 
        v.ViewID,
        v.SessionClientId,
        v.SessionServerId,
        v.Status,
        v.StartTime,
        v.EndTime,
        TIMESTAMPDIFF(MINUTE, v.StartTime, COALESCE(v.EndTime, NOW())) AS DurationMinutes,
        (SELECT COUNT(*) FROM keystrokes k WHERE k.ViewID = v.ViewID) AS KeystrokeCount,
        (SELECT COUNT(*) FROM window_logs w WHERE w.ViewID = v.ViewID) AS WindowLogCount,
        (SELECT COUNT(*) FROM screen_captures s WHERE s.ViewID = v.ViewID) AS ScreenCaptureCount,
        (SELECT COUNT(*) FROM control_sessions c WHERE c.ViewID = v.ViewID) AS ControlSessionCount,
        (SELECT COUNT(*) FROM file_transfers f WHERE f.ViewID = v.ViewID) AS FileTransferCount,
        (SELECT COUNT(*) FROM security_alerts a WHERE a.ViewID = v.ViewID) AS AlertCount
    FROM `View` v
    WHERE v.ViewID = p_view_id;
END //
DELIMITER ;

-- Procedure: Lấy thông tin user theo username
DELIMITER //
CREATE PROCEDURE IF NOT EXISTS GetUserByUsername(IN p_username VARCHAR(100))
BEGIN
    SELECT 
        UserID,
        Username,
        FullName,
        Email,
        Role,
        CreatedAt,
        LastLogin
    FROM Users
    WHERE Username = p_username;
END //
DELIMITER ;

-- =====================================================
-- DỮ LIỆU MẪU (Optional - Admin mặc định)
-- =====================================================

-- Tạo tài khoản admin mặc định (password: admin123)
-- Hash được tạo bằng Argon2 trong Python
-- Bạn có thể tạo user qua ứng dụng thay vì chạy script này

-- INSERT IGNORE INTO Users (Username, PasswordHash, FullName, Email, Role)
-- VALUES ('admin', '$argon2id$v=19$m=65536,t=2,p=2$...', 'Administrator', 'admin@localhost', 'admin');

-- =====================================================
-- SAMPLE QUERIES (Truy vấn mẫu tham khảo)
-- =====================================================
/*
-- Lấy tất cả users
SELECT * FROM Users;

-- Lấy tất cả sessions của một user
SELECT s.* FROM Session s 
INNER JOIN Users u ON s.UserID = u.UserID 
WHERE u.Username = 'your_username';

-- Lấy tất cả View sessions active
SELECT * FROM View WHERE EndTime IS NULL;

-- Lấy keystrokes của một phiên View
SELECT * FROM keystrokes WHERE ViewID = 'uuid-here' ORDER BY LoggedAt;

-- Lấy window logs của một phiên View
SELECT * FROM window_logs WHERE ViewID = 'uuid-here' ORDER BY LoggedAt;

-- Lấy thống kê phiên
CALL GetViewSummary('uuid-here');

-- Xem thống kê tất cả phiên
SELECT * FROM view_session_statistics;
*/
