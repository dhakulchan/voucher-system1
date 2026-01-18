-- Migration: Create voucher_albums table
-- Purpose: Store voucher album images for Voucher Library feature
-- Date: 2025-11-30

-- Create voucher_albums table
CREATE TABLE IF NOT EXISTS voucher_albums (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    remarks TEXT,
    image_path VARCHAR(500) NOT NULL,
    file_size INT NOT NULL COMMENT 'File size in bytes',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_created_at (created_at),
    INDEX idx_title (title)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Verify table creation
SELECT 'Table voucher_albums created successfully' AS status;

-- Show table structure
DESCRIBE voucher_albums;
