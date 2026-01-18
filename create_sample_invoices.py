"""
Test script to create sample invoice data
"""
from app import create_app
from extensions import db
from models.account_invoice import InvoiceHongKong, InvoiceThai
from datetime import date, datetime
from decimal import Decimal

def create_sample_invoices():
    """Create sample invoices for testing"""
    app = create_app()
    
    with app.app_context():
        try:
            # Check if we already have data
            hk_count = InvoiceHongKong.query.count()
            thai_count = InvoiceThai.query.count()
            
            if hk_count > 0 or thai_count > 0:
                print(f"✅ Found existing data: {hk_count} HK invoices, {thai_count} Thai invoices")
                return
            
            print("Creating sample Hong Kong invoice...")
            hk_invoice = InvoiceHongKong(
                customer_id=None,
                cust_name="Dhakulchan Travel Service (Thailand) Co.Ltd",
                company_name="Dhakulchan Travel Service",
                company_address="710, 716 Prachaulid Road, Samsennok, Huai Kwang, Bangkok",
                company_tel="+662 2744216",
                company_taxid="0105540059068",
                company_contact="Chookiat",
                total_pax=25,
                arrival_date=date(2024, 4, 1),
                departure_date=date(2024, 4, 30),
                guest_list="Sample Guest 1\nSample Guest 2\nSample Guest 3",
                flight_info="Flight: TG123\nDeparture: 10:00\nArrival: 14:00",
                air_ticket_cost=Decimal('108250.00'),
                transportation_fee=Decimal('5000.00'),
                advance_expense=Decimal('2000.00'),
                tour_fee=Decimal('15000.00'),
                vat=Decimal('0.00'),
                withholding_tax=Decimal('0.00'),
                total_tour_fee=Decimal('130250.00')
            )
            db.session.add(hk_invoice)
            
            print("Creating sample Thai invoice...")
            thai_invoice = InvoiceThai(
                customer_id=None,
                cust_name="บริษัท ตระกูลจันทร์ ทราเวล เซอร์วิส (ประเทศไทย) จำกัด",
                company_name="บริษัท ตระกูลจันทร์ ทราเวล เซอร์วิส",
                company_address="710,716 ถนนประชาอุทิศ แขวงสามเสนนอก เขตห้วยขวาง กรุงเทพมหานคร 10400",
                company_tel="0-2274-4216",
                company_taxid="0105540059068",
                company_contact="ชูเกียรติ",
                total_pax=1,
                arrival_date=date(2025, 11, 9),
                departure_date=date(2025, 11, 15),
                guest_list="นาย สมชาย ใจดี\nนาง สมหญิง ใจดี",
                flight_info="เที่ยวบินที่: TG456\nออกเดินทาง: 09:00\nถึง: 13:00",
                air_ticket_cost=Decimal('1166.00'),
                transportation_fee=Decimal('500.00'),
                advance_expense=Decimal('300.00'),
                tour_fee=Decimal('800.00'),
                vat=Decimal('81.62'),
                withholding_tax=Decimal('0.00'),
                total_tour_fee=Decimal('2847.62')
            )
            db.session.add(thai_invoice)
            
            db.session.commit()
            
            print("✅ Sample invoices created successfully!")
            print(f"   - 1 Hong Kong invoice (Total: HKD 130,250.00)")
            print(f"   - 1 Thai invoice (Total: THB 2,847.62)")
            print("\nYou can now view them at: http://localhost:5001/account-report/invoices")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error creating sample invoices: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    create_sample_invoices()
