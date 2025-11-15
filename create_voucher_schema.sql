-- Create comprehensive voucher system database schema
-- Enhanced schema with workflow support, social sharing, and unified PDF generation

USE voucher_db;

-- Customers table
CREATE TABLE customers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE,
    phone VARCHAR(20),
    address TEXT,
    city VARCHAR(100),
    country VARCHAR(100),
    postal_code VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_email (email),
    INDEX idx_phone (phone),
    INDEX idx_name (first_name, last_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Number sequences for booking, quote, voucher numbering
CREATE TABLE number_sequences (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sequence_type ENUM('booking', 'quote', 'voucher') NOT NULL UNIQUE,
    current_number INT NOT NULL DEFAULT 1000,
    prefix VARCHAR(10) NOT NULL DEFAULT '',
    suffix VARCHAR(10) NOT NULL DEFAULT '',
    format_template VARCHAR(50) NOT NULL DEFAULT '%s%06d%s',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Insert default sequences
INSERT INTO number_sequences (sequence_type, current_number, prefix, suffix, format_template) VALUES
('booking', 1000, 'BK', '', 'BK%06d'),
('quote', 2000, 'QT', '', 'QT%06d'),
('voucher', 3000, 'VC', '', 'VC%06d');

-- Bookings table (enhanced workflow)
CREATE TABLE bookings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    booking_number VARCHAR(50) UNIQUE NOT NULL,
    customer_id INT NOT NULL,
    booking_date DATE NOT NULL,
    return_date DATE,
    adults INT DEFAULT 1,
    children INT DEFAULT 0,
    infants INT DEFAULT 0,
    total_guests INT GENERATED ALWAYS AS (adults + children + infants) STORED,
    
    -- Workflow status
    status ENUM('draft', 'confirmed', 'cancelled', 'completed') DEFAULT 'draft',
    
    -- Flight information
    departure_flight VARCHAR(100),
    departure_time TIME,
    arrival_flight VARCHAR(100), 
    arrival_time TIME,
    departure_airport VARCHAR(100),
    arrival_airport VARCHAR(100),
    
    -- Guest list and special requirements
    guest_list TEXT,
    special_requirements TEXT,
    dietary_requirements TEXT,
    
    -- Financial fields
    total_amount DECIMAL(10,2) DEFAULT 0.00,
    deposit_amount DECIMAL(10,2) DEFAULT 0.00,
    balance_amount DECIMAL(10,2) GENERATED ALWAYS AS (total_amount - deposit_amount) STORED,
    is_paid BOOLEAN DEFAULT FALSE,
    payment_status ENUM('unpaid', 'partial', 'paid', 'refunded') DEFAULT 'unpaid',
    payment_method VARCHAR(50),
    payment_reference VARCHAR(100),
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    confirmed_at TIMESTAMP NULL,
    
    -- Metadata
    notes TEXT,
    internal_notes TEXT,
    
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    INDEX idx_booking_number (booking_number),
    INDEX idx_customer (customer_id),
    INDEX idx_status (status),
    INDEX idx_booking_date (booking_date),
    INDEX idx_payment_status (payment_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Quotes table (generated from confirmed bookings)
CREATE TABLE quotes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    quote_number VARCHAR(50) UNIQUE NOT NULL,
    booking_id INT NOT NULL,
    
    -- Quote status workflow
    status ENUM('draft', 'sent', 'accepted', 'rejected', 'expired') DEFAULT 'draft',
    
    -- Pricing details
    subtotal DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    tax_amount DECIMAL(10,2) DEFAULT 0.00,
    discount_amount DECIMAL(10,2) DEFAULT 0.00,
    total_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    
    -- Validity
    valid_until DATE,
    
    -- Quote generation info
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sent_at TIMESTAMP NULL,
    accepted_at TIMESTAMP NULL,
    
    -- Document paths
    pdf_path VARCHAR(255),
    png_path VARCHAR(255),
    
    -- Templates used
    template_used VARCHAR(100) DEFAULT 'quote_template_final_qt.html',
    
    -- Metadata
    notes TEXT,
    terms_conditions TEXT,
    
    FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE CASCADE,
    INDEX idx_quote_number (quote_number),
    INDEX idx_booking (booking_id),
    INDEX idx_status (status),
    INDEX idx_valid_until (valid_until)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Vouchers table (generated from paid quotes) 
CREATE TABLE vouchers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    voucher_number VARCHAR(50) UNIQUE NOT NULL,
    quote_id INT NOT NULL,
    booking_id INT NOT NULL,
    
    -- Voucher status
    status ENUM('active', 'used', 'expired', 'cancelled') DEFAULT 'active',
    
    -- Voucher details
    issue_date DATE NOT NULL,
    expiry_date DATE,
    
    -- Service details
    service_date DATE,
    service_time TIME,
    pickup_location VARCHAR(255),
    dropoff_location VARCHAR(255),
    
    -- Document paths
    pdf_path VARCHAR(255),
    png_path VARCHAR(255),
    
    -- QR code for verification
    qr_code_data TEXT,
    qr_code_path VARCHAR(255),
    
    -- Usage tracking
    used_at TIMESTAMP NULL,
    used_by VARCHAR(100),
    
    -- Templates used
    template_used VARCHAR(100) DEFAULT 'voucher_template_final.html',
    
    -- Metadata
    notes TEXT,
    special_instructions TEXT,
    
    FOREIGN KEY (quote_id) REFERENCES quotes(id) ON DELETE CASCADE,
    FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE CASCADE,
    INDEX idx_voucher_number (voucher_number),
    INDEX idx_quote (quote_id),
    INDEX idx_booking (booking_id),
    INDEX idx_status (status),
    INDEX idx_service_date (service_date),
    INDEX idx_expiry_date (expiry_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Document shares table (for social sharing tracking)
CREATE TABLE document_shares (
    id INT AUTO_INCREMENT PRIMARY KEY,
    document_type ENUM('quote', 'voucher') NOT NULL,
    document_id INT NOT NULL,
    share_token VARCHAR(100) UNIQUE NOT NULL,
    share_type ENUM('line_oa', 'line_message', 'facebook', 'twitter', 'email', 'public_link') NOT NULL,
    
    -- Share tracking
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NULL,
    accessed_count INT DEFAULT 0,
    last_accessed_at TIMESTAMP NULL,
    
    -- Share metadata
    shared_by VARCHAR(100),
    recipient_info TEXT,
    
    INDEX idx_document (document_type, document_id),
    INDEX idx_share_token (share_token),
    INDEX idx_share_type (share_type),
    INDEX idx_expires_at (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Booking products/services table
CREATE TABLE booking_products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    booking_id INT NOT NULL,
    product_name VARCHAR(200) NOT NULL,
    product_type VARCHAR(100),
    quantity INT DEFAULT 1,
    unit_price DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    total_price DECIMAL(10,2) GENERATED ALWAYS AS (quantity * unit_price) STORED,
    description TEXT,
    
    FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE CASCADE,
    INDEX idx_booking (booking_id),
    INDEX idx_product_type (product_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Activity log for workflow tracking
CREATE TABLE activity_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    entity_type ENUM('booking', 'quote', 'voucher') NOT NULL,
    entity_id INT NOT NULL,
    action VARCHAR(100) NOT NULL,
    description TEXT,
    old_status VARCHAR(50),
    new_status VARCHAR(50),
    user_id VARCHAR(100),
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_entity (entity_type, entity_id),
    INDEX idx_action (action),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Document generation log
CREATE TABLE document_generations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    document_type ENUM('quote_pdf', 'quote_png', 'voucher_pdf', 'voucher_png') NOT NULL,
    entity_type ENUM('quote', 'voucher') NOT NULL,
    entity_id INT NOT NULL,
    template_used VARCHAR(100),
    generation_status ENUM('success', 'error') NOT NULL,
    file_path VARCHAR(255),
    file_size INT,
    generation_time_ms INT,
    error_message TEXT,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_entity (entity_type, entity_id),
    INDEX idx_document_type (document_type),
    INDEX idx_status (generation_status),
    INDEX idx_generated_at (generated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Create views for common queries
CREATE VIEW booking_summary AS
SELECT 
    b.id,
    b.booking_number,
    CONCAT(c.first_name, ' ', c.last_name) as customer_name,
    c.email,
    c.phone,
    b.booking_date,
    b.total_guests,
    b.status as booking_status,
    b.total_amount,
    b.payment_status,
    CASE WHEN q.id IS NOT NULL THEN 'Yes' ELSE 'No' END as has_quote,
    CASE WHEN v.id IS NOT NULL THEN 'Yes' ELSE 'No' END as has_voucher
FROM bookings b
JOIN customers c ON b.customer_id = c.id
LEFT JOIN quotes q ON b.id = q.booking_id
LEFT JOIN vouchers v ON b.id = v.booking_id;

CREATE VIEW quote_summary AS
SELECT 
    q.id,
    q.quote_number,
    b.booking_number,
    CONCAT(c.first_name, ' ', c.last_name) as customer_name,
    q.status as quote_status,
    q.total_amount,
    q.valid_until,
    q.generated_at,
    CASE WHEN v.id IS NOT NULL THEN 'Yes' ELSE 'No' END as has_voucher
FROM quotes q
JOIN bookings b ON q.booking_id = b.id
JOIN customers c ON b.customer_id = c.id
LEFT JOIN vouchers v ON q.id = v.quote_id;

CREATE VIEW voucher_summary AS
SELECT 
    v.id,
    v.voucher_number,
    q.quote_number,
    b.booking_number,
    CONCAT(c.first_name, ' ', c.last_name) as customer_name,
    v.status as voucher_status,
    v.service_date,
    v.expiry_date,
    v.pickup_location,
    v.issue_date
FROM vouchers v
JOIN quotes q ON v.quote_id = q.id
JOIN bookings b ON v.booking_id = b.id
JOIN customers c ON b.customer_id = c.id;

-- Triggers for automatic number generation
DELIMITER $$

CREATE TRIGGER booking_number_generator
BEFORE INSERT ON bookings
FOR EACH ROW
BEGIN
    DECLARE next_num INT;
    DECLARE seq_format VARCHAR(50);
    
    -- Get next booking number
    SELECT current_number + 1, format_template 
    INTO next_num, seq_format
    FROM number_sequences 
    WHERE sequence_type = 'booking';
    
    -- Update sequence
    UPDATE number_sequences 
    SET current_number = next_num 
    WHERE sequence_type = 'booking';
    
    -- Generate booking number
    SET NEW.booking_number = CONCAT('BK', DATE_FORMAT(NOW(), '%Y%m%d'), LPAD(next_num, 6, '0'));
END$$

CREATE TRIGGER quote_number_generator
BEFORE INSERT ON quotes
FOR EACH ROW
BEGIN
    DECLARE next_num INT;
    
    -- Get next quote number
    SELECT current_number + 1 
    INTO next_num
    FROM number_sequences 
    WHERE sequence_type = 'quote';
    
    -- Update sequence
    UPDATE number_sequences 
    SET current_number = next_num 
    WHERE sequence_type = 'quote';
    
    -- Generate quote number
    SET NEW.quote_number = CONCAT('QT', DATE_FORMAT(NOW(), '%Y%m%d'), LPAD(next_num, 6, '0'));
END$$

CREATE TRIGGER voucher_number_generator
BEFORE INSERT ON vouchers
FOR EACH ROW
BEGIN
    DECLARE next_num INT;
    
    -- Get next voucher number
    SELECT current_number + 1 
    INTO next_num
    FROM number_sequences 
    WHERE sequence_type = 'voucher';
    
    -- Update sequence
    UPDATE number_sequences 
    SET current_number = next_num 
    WHERE sequence_type = 'voucher';
    
    -- Generate voucher number
    SET NEW.voucher_number = CONCAT('VC', DATE_FORMAT(NOW(), '%Y%m%d'), LPAD(next_num, 6, '0'));
END$$

-- Activity logging triggers
CREATE TRIGGER booking_activity_log
AFTER UPDATE ON bookings
FOR EACH ROW
BEGIN
    IF OLD.status != NEW.status THEN
        INSERT INTO activity_logs (entity_type, entity_id, action, description, old_status, new_status)
        VALUES ('booking', NEW.id, 'status_change', 
                CONCAT('Booking status changed from ', OLD.status, ' to ', NEW.status),
                OLD.status, NEW.status);
    END IF;
END$$

CREATE TRIGGER quote_activity_log
AFTER UPDATE ON quotes
FOR EACH ROW
BEGIN
    IF OLD.status != NEW.status THEN
        INSERT INTO activity_logs (entity_type, entity_id, action, description, old_status, new_status)
        VALUES ('quote', NEW.id, 'status_change',
                CONCAT('Quote status changed from ', OLD.status, ' to ', NEW.status),
                OLD.status, NEW.status);
    END IF;
END$$

CREATE TRIGGER voucher_activity_log
AFTER UPDATE ON vouchers
FOR EACH ROW
BEGIN
    IF OLD.status != NEW.status THEN
        INSERT INTO activity_logs (entity_type, entity_id, action, description, old_status, new_status)
        VALUES ('voucher', NEW.id, 'status_change',
                CONCAT('Voucher status changed from ', OLD.status, ' to ', NEW.status),
                OLD.status, NEW.status);
    END IF;
END$$

DELIMITER ;

-- Create indexes for performance
CREATE INDEX idx_bookings_composite ON bookings(status, booking_date, customer_id);
CREATE INDEX idx_quotes_composite ON quotes(status, valid_until, booking_id);
CREATE INDEX idx_vouchers_composite ON vouchers(status, service_date, expiry_date);

-- Show created tables
SHOW TABLES;

SELECT 'Database schema created successfully!' as status;