"""
Alternative PDF Generator using WeasyPrint for better Thai font support
"""
import os
from datetime import datetime
import weasyprint
from io import BytesIO

class ThaiPDFService:
    def __init__(self):
        self.output_dir = "static/generated"
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
    
    def generate_thai_service_proposal(self, booking):
        """Generate Service Proposal PDF with proper Thai support using WeasyPrint"""
        
        # Create HTML content with Thai text
        html_content = f"""
        <!DOCTYPE html>
        <html lang="th">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Service Proposal</title>
            <style>
                body {{
                    font-family: 'SF Pro Display', 'Helvetica Neue', Arial, sans-serif;
                    font-size: 12px;
                    line-height: 1.4;
                    margin: 20px;
                    color: #333;
                }}
                
                .thai-text {{
                    font-family: 'Thonburi', 'SF Pro Display', 'Helvetica Neue', Arial, sans-serif;
                }}
                
                .header {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 30px;
                    border-bottom: 2px solid #e0e0e0;
                    padding-bottom: 20px;
                }}
                
                .logo {{
                    font-size: 24px;
                    font-weight: bold;
                    color: #1976d2;
                }}
                
                .reference {{
                    font-size: 14px;
                    font-weight: bold;
                }}
                
                .section {{
                    margin-bottom: 20px;
                }}
                
                .section-title {{
                    font-size: 16px;
                    font-weight: bold;
                    margin-bottom: 10px;
                    color: #1976d2;
                }}
                
                .details-table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-bottom: 20px;
                }}
                
                .details-table td {{
                    padding: 8px;
                    border: 1px solid #ddd;
                    vertical-align: top;
                }}
                
                .details-table .label {{
                    font-weight: bold;
                    background-color: #f5f5f5;
                    width: 30%;
                }}
                
                .thai-terms {{
                    background-color: #f9f9f9;
                    padding: 15px;
                    border-left: 4px solid #1976d2;
                    margin-top: 20px;
                    font-family: 'Thonburi', 'SF Pro Display', 'Helvetica Neue', Arial, sans-serif;
                }}
                
                .thai-terms ul {{
                    margin: 0;
                    padding-left: 20px;
                }}
                
                .thai-terms li {{
                    margin-bottom: 8px;
                    line-height: 1.6;
                }}
            </style>
                
                .header {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 30px;
                    border-bottom: 2px solid #e0e0e0;
                    padding-bottom: 20px;
                }}
                
                .logo {{
                    font-size: 24px;
                    font-weight: bold;
                    color: #1976d2;
                }}
                
                .reference {{
                    font-size: 14px;
                    font-weight: bold;
                }}
                
                .section {{
                    margin-bottom: 20px;
                }}
                
                .section-title {{
                    font-size: 16px;
                    font-weight: bold;
                    margin-bottom: 10px;
                    color: #1976d2;
                }}
                
                .details-table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-bottom: 20px;
                }}
                
                .details-table td {{
                    padding: 8px;
                    border: 1px solid #ddd;
                    vertical-align: top;
                }}
                
                .details-table .label {{
                    font-weight: bold;
                    background-color: #f5f5f5;
                    width: 30%;
                }}
                
                .thai-terms {{
                    background-color: #f9f9f9;
                    padding: 15px;
                    border-left: 4px solid #1976d2;
                    margin-top: 20px;
                }}
                
                .thai-terms ul {{
                    margin: 0;
                    padding-left: 20px;
                }}
                
                .thai-terms li {{
                    margin-bottom: 8px;
                    line-height: 1.6;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <div class="logo">D.C.T.S 28th Anniversary</div>
                <div class="reference">Reference: {booking.booking_reference}</div>
            </div>
            
            <div class="section">
                <div class="section-title">ข้อมูลการจอง / Booking Information</div>
                <table class="details-table">
                    <tr>
                        <td class="label">ชื่อผู้จอง / Party Name:</td>
                        <td>{getattr(booking, 'party_name', booking.customer.name)}</td>
                    </tr>
                    <tr>
                        <td class="label">โทรศัพท์ / Phone:</td>
                        <td>{booking.customer.phone}</td>
                    </tr>
                    <tr>
                        <td class="label">วันที่เดินทาง / Travel Date:</td>
                        <td>{booking.arrival_date.strftime('%d %B %Y') if booking.arrival_date else ''}</td>
                    </tr>
                    <tr>
                        <td class="label">จำนวนผู้เดินทาง / Passengers:</td>
                        <td>{booking.total_pax} คน (ผู้ใหญ่ {booking.adults} เด็ก {booking.children} ทารก {booking.infants})</td>
                    </tr>
                </table>
            </div>
            
            <div class="section">
                <div class="section-title">รายละเอียดบริการ / Service Details</div>
                <p><strong>ประเภทการจอง / Booking Type:</strong> {booking.booking_type.upper()}</p>
                <p><strong>รายละเอียด / Description:</strong> {booking.description or 'N/A'}</p>
                {'<p><strong>โรงแรม / Hotel:</strong> ' + booking.hotel_name + '</p>' if hasattr(booking, 'hotel_name') and booking.hotel_name else ''}
            </div>
            
            <div class="section">
                <div class="section-title">ข้อมูลการชำระเงิน / Payment Information</div>
                <p><strong>ราคารวม:</strong> THB {getattr(booking, 'total_amount', getattr(booking, 'total_price', 0)):,.2f}</p>
            </div>
            
            <div class="section">
                <div class="section-title">คำร้องขอพิเศษ / Special Requests</div>
                <p>{booking.special_request or 'None'}</p>
            </div>
            
            <div class="thai-terms">
                <div class="section-title">เงื่อนไขและข้อกำหนด / Terms & Conditions</div>
                <ul>
                    <li>เอกสารสถานเบียนเพื่อใช้ในการดำเนินการจอง</li>
                    <li>ราคาและรายละเอียดที่ปรากฏการเปลี่ยนแปลงโดยไม่แจ้งให้ทราบล่วงหน้า จนกว่าจะได้รับการยืนยัน</li>
                    <li>กรุณายืนยันการจองโดยชำระเงินมัดจำ เพื่อให้ราคาและสิทธิ์ในการจอง</li>
                    <li>ใบเสนอราคานี้มีอายุ 4 ชั่วโมง นับจากวันและเวลาที่ออก เว้นแต่จะระบุไว้เป็นอย่างอื่น</li>
                    <li>การเปลี่ยนแปลงวันเดินทาง จํานวนผู้เดินทาง หรือรายละเอียดบริการ อาจมีผลต่อราคา</li>
                </ul>
            </div>
        </body>
        </html>
        """
        
        # Generate PDF using WeasyPrint
        filename = f"thai_service_proposal_{booking.booking_reference}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        filepath = os.path.join(self.output_dir, filename)
        
        try:
            # Convert HTML to PDF with Thai font support
            weasyprint.HTML(string=html_content).write_pdf(filepath)
            from utils.logging_config import get_logger as _get_logger2
            _logger = _get_logger2(__name__)
            _logger.info("Thai PDF generated successfully %s", filename)
            return filename
        except Exception as e:
            from utils.logging_config import get_logger as _get_logger3
            _logger = _get_logger3(__name__)
            _logger.error("WeasyPrint PDF generation failed: %s", e, exc_info=True)
            return None
