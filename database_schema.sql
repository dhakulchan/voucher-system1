-- Dhakul Chan Group Smart System V.202501 Database Schema
-- MySQL/MariaDB Script

-- Create database
CREATE DATABASE IF NOT EXISTS tour_voucher_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE tour_voucher_db;

-- Create user (optional - for production)
-- CREATE USER 'voucher_user'@'localhost' IDENTIFIED BY 'your_secure_password';
-- GRANT ALL PRIVILEGES ON tour_voucher_db.* TO 'voucher_user'@'localhost';
-- FLUSH PRIVILEGES;

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(80) NOT NULL UNIQUE,
    email VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_username (username),
    INDEX idx_email (email)
);

-- Customers table
CREATE TABLE IF NOT EXISTS customers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(50) NOT NULL,
    address TEXT,
    invoice_ninja_client_id INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_email (email),
    INDEX idx_phone (phone),
    INDEX idx_name (name)
);

-- Bookings table
CREATE TABLE IF NOT EXISTS bookings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    booking_reference VARCHAR(100) NOT NULL UNIQUE,
    
    -- Invoice Ninja Integration
    quote_id INT,
    invoice_id INT,
    
    -- Booking Details
    booking_type VARCHAR(50) NOT NULL, -- 'tour', 'hotel', 'transport'
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'confirmed', 'cancelled', 'completed'
    
    -- Travel Information
    arrival_date DATE,
    departure_date DATE,
    traveling_period_start DATE,
    traveling_period_end DATE,
    
    -- Guest Information
    total_pax INT DEFAULT 1,
    guest_list TEXT, -- JSON string
    
    -- Hotel RO Specific Fields
    agency_reference VARCHAR(100),
    hotel_name VARCHAR(255),
    room_type VARCHAR(100),
    special_request TEXT,
    
    -- MPV Booking Specific Fields
    pickup_point VARCHAR(255),
    destination VARCHAR(255),
    pickup_time TIME,
    vehicle_type VARCHAR(100),
    
    -- Tour Voucher Specific Fields
    internal_note TEXT,
    admin_notes TEXT,
    manager_memos TEXT,
    flight_info TEXT,
    daily_services TEXT, -- JSON string
    
    -- Financial
    total_amount DECIMAL(10, 2),
    currency VARCHAR(10) DEFAULT 'THB',
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_by INT,
    
    -- Foreign Keys
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL,
    
    -- Indexes
    INDEX idx_booking_reference (booking_reference),
    INDEX idx_booking_type (booking_type),
    INDEX idx_status (status),
    INDEX idx_customer_id (customer_id),
    INDEX idx_dates (arrival_date, departure_date),
    INDEX idx_created_at (created_at)
);

-- Insert default admin user
INSERT INTO users (username, email, password_hash, is_admin) 
VALUES ('admin', 'admin@example.com', 'pbkdf2:sha256:260000$salt$hash', TRUE)
ON DUPLICATE KEY UPDATE username=username;

-- Sample data (optional)
INSERT INTO customers (name, email, phone, address) VALUES
('John Doe', 'john.doe@email.com', '+66-123-456-789', '123 Main St, Bangkok, Thailand'),
('Jane Smith', 'jane.smith@email.com', '+66-987-654-321', '456 Tourism Ave, Phuket, Thailand')
ON DUPLICATE KEY UPDATE name=name;

-- Create indexes for performance
CREATE INDEX idx_bookings_customer_type ON bookings(customer_id, booking_type);
CREATE INDEX idx_bookings_status_date ON bookings(status, created_at);
CREATE INDEX idx_customers_name_email ON customers(name, email);

-- Views for reporting
CREATE OR REPLACE VIEW booking_summary AS
SELECT 
    b.id,
    b.booking_reference,
    b.booking_type,
    b.status,
    c.name as customer_name,
    c.email as customer_email,
    b.total_amount,
    b.currency,
    b.created_at,
    CASE 
        WHEN b.booking_type = 'hotel' THEN b.hotel_name
        WHEN b.booking_type = 'transport' THEN CONCAT(b.pickup_point, ' → ', b.destination)
        WHEN b.booking_type = 'tour' THEN CONCAT(b.traveling_period_start, ' to ', b.traveling_period_end)
        ELSE 'N/A'
    END as booking_details
FROM bookings b
JOIN customers c ON b.customer_id = c.id;

-- Revenue summary view
CREATE OR REPLACE VIEW revenue_summary AS
SELECT 
    DATE(created_at) as booking_date,
    booking_type,
    status,
    COUNT(*) as booking_count,
    SUM(total_amount) as total_revenue,
    AVG(total_amount) as avg_booking_value
FROM bookings
WHERE status IN ('confirmed', 'completed')
GROUP BY DATE(created_at), booking_type, status
ORDER BY booking_date DESC;

-- Customer statistics view
CREATE OR REPLACE VIEW customer_stats AS
SELECT 
    c.id,
    c.name,
    c.email,
    COUNT(b.id) as total_bookings,
    SUM(CASE WHEN b.status IN ('confirmed', 'completed') THEN b.total_amount ELSE 0 END) as total_spent,
    MAX(b.created_at) as last_booking_date,
    c.created_at as customer_since
FROM customers c
LEFT JOIN bookings b ON c.id = b.customer_id
GROUP BY c.id, c.name, c.email, c.created_at;

-- Success message
SELECT 'Database schema created successfully!' as message;
