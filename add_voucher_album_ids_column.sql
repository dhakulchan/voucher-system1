-- Migration: Add voucher_album_ids column to bookings table
-- Purpose: Store selected voucher album IDs from library for display in voucher PDF/PNG
-- Date: 2025-11-30

-- Add voucher_album_ids column
ALTER TABLE bookings 
ADD COLUMN IF NOT EXISTS voucher_album_ids TEXT 
COMMENT 'JSON string of selected voucher album IDs from library'
AFTER voucher_images;

-- Verify column creation
SELECT 'Column voucher_album_ids added successfully' AS status;

-- Show voucher-related columns
SELECT COLUMN_NAME, COLUMN_TYPE, COLUMN_COMMENT 
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE() 
AND TABLE_NAME = 'bookings' 
AND COLUMN_NAME LIKE '%voucher%';
