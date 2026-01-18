"""
Migration script to create invoice_hongkong and invoice_thai tables
"""
from app import create_app
from extensions import db
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_invoice_tables():
    """Create invoice_hongkong and invoice_thai tables"""
    app = create_app()
    
    with app.app_context():
        try:
            from sqlalchemy import text
            
            # Create invoice_hongkong table
            logger.info("Creating invoice_hongkong table...")
            with db.engine.connect() as conn:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS invoice_hongkong (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        customer_id INT,
                        cust_name VARCHAR(255),
                        company_name VARCHAR(255),
                        company_address TEXT,
                        company_tel VARCHAR(50),
                        company_taxid VARCHAR(50),
                        company_contact VARCHAR(255),
                        total_pax INT DEFAULT 0,
                        arrival_date DATE,
                        departure_date DATE,
                        guest_list TEXT,
                        flight_info TEXT,
                        air_ticket_cost DECIMAL(12, 2) DEFAULT 0.00,
                        transportation_fee DECIMAL(12, 2) DEFAULT 0.00,
                        advance_expense DECIMAL(12, 2) DEFAULT 0.00,
                        tour_fee DECIMAL(12, 2) DEFAULT 0.00,
                        vat DECIMAL(12, 2) DEFAULT 0.00,
                        withholding_tax DECIMAL(12, 2) DEFAULT 0.00,
                        total_tour_fee DECIMAL(12, 2) DEFAULT 0.00,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE SET NULL
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                """))
                conn.commit()
            logger.info("invoice_hongkong table created successfully")
            
            # Create invoice_thai table
            logger.info("Creating invoice_thai table...")
            with db.engine.connect() as conn:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS invoice_thai (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        customer_id INT,
                        cust_name VARCHAR(255),
                        company_name VARCHAR(255),
                        company_address TEXT,
                        company_tel VARCHAR(50),
                        company_taxid VARCHAR(50),
                        company_contact VARCHAR(255),
                        total_pax INT DEFAULT 0,
                        arrival_date DATE,
                        departure_date DATE,
                        guest_list TEXT,
                        flight_info TEXT,
                        air_ticket_cost DECIMAL(12, 2) DEFAULT 0.00,
                        transportation_fee DECIMAL(12, 2) DEFAULT 0.00,
                        advance_expense DECIMAL(12, 2) DEFAULT 0.00,
                        tour_fee DECIMAL(12, 2) DEFAULT 0.00,
                        vat DECIMAL(12, 2) DEFAULT 0.00,
                        withholding_tax DECIMAL(12, 2) DEFAULT 0.00,
                        total_tour_fee DECIMAL(12, 2) DEFAULT 0.00,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE SET NULL
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                """))
                conn.commit()
            logger.info("invoice_thai table created successfully")
            
            logger.info("All invoice tables created successfully!")
            
        except Exception as e:
            logger.error(f"Error creating tables: {str(e)}")
            raise

if __name__ == '__main__':
    create_invoice_tables()
