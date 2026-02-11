-- Migration: Add customer_id to users table
-- This links users to their customer records for the points system

-- Add customer_id column
ALTER TABLE users ADD COLUMN customer_id INT NULL;

-- Add foreign key constraint
ALTER TABLE users ADD CONSTRAINT fk_users_customers 
    FOREIGN KEY (customer_id) 
    REFERENCES customers(id);

-- Link existing users to customers by matching email addresses
UPDATE users u
INNER JOIN customers c ON u.email = c.email
SET u.customer_id = c.id
WHERE u.role = 'Customer' AND u.customer_id IS NULL;

-- Show results
SELECT 'Migration completed' AS status;
SELECT COUNT(*) AS linked_users FROM users WHERE customer_id IS NOT NULL;
