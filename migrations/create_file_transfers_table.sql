-- Bảng lưu lịch sử truyền file
CREATE TABLE IF NOT EXISTS file_transfers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sender_id VARCHAR(100) NOT NULL COMMENT 'ID của người gửi (manager hoặc client)',
    sender_type ENUM('manager', 'client') NOT NULL COMMENT 'Loại người gửi',
    receiver_id VARCHAR(100) NOT NULL COMMENT 'ID của người nhận (manager hoặc client)',
    receiver_type ENUM('manager', 'client') NOT NULL COMMENT 'Loại người nhận',
    filename VARCHAR(255) NOT NULL COMMENT 'Tên file',
    filesize BIGINT NOT NULL COMMENT 'Kích thước file (bytes)',
    file_hash VARCHAR(64) COMMENT 'Hash của file (SHA256) để xác minh tính toàn vẹn',
    status ENUM('pending', 'sending', 'completed', 'failed') DEFAULT 'pending' COMMENT 'Trạng thái transfer',
    error_message TEXT COMMENT 'Lỗi nếu có',
    transfer_started_at TIMESTAMP NULL DEFAULT NULL COMMENT 'Thời gian bắt đầu transfer',
    transfer_completed_at TIMESTAMP NULL DEFAULT NULL COMMENT 'Thời gian hoàn thành transfer',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_sender (sender_id, sender_type),
    INDEX idx_receiver (receiver_id, receiver_type),
    INDEX idx_created_at (created_at),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Lịch sử truyền file';
