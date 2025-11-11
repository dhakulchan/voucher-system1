# services/thai_pdf_generator.py - ตัวสร้าง PDF ภาษาไทย
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib import colors
    from reportlab.lib.units import inch, cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    REPORTLAB_AVAILABLE = True
except ImportError as e:
    from utils.logging_config import get_logger as _get_logger
    _tmp_logger = _get_logger(__name__)
    _tmp_logger.warning("ReportLab not available: %s", e)
    REPORTLAB_AVAILABLE = False

from datetime import datetime
import os
from config import Config
from services.qr_generator import QRGenerator
from utils.thai_utils import thai_date_format, thai_datetime_format, format_thai_currency, thai_currency_to_text
from utils.logging_config import get_logger

logger = get_logger(__name__)

class ThaiPDFGenerator:
    def __init__(self):
        if not REPORTLAB_AVAILABLE:
            logger.warning("ReportLab not available, PDF generation will be limited")
        
        self.output_dir = 'static/generated'
        os.makedirs(self.output_dir, exist_ok=True)
        self.qr_generator = QRGenerator()
        
        if REPORTLAB_AVAILABLE:
            # ลงทะเบียนฟอนต์ไทย
            self.setup_thai_fonts()
            
            # สร้าง styles สำหรับภาษาไทย
            self.setup_thai_styles()
    
    def setup_thai_fonts(self):
        """ตั้งค่าฟอนต์ภาษาไทย"""
        try:
            # ใช้ฟอนต์ระบบที่รองรับภาษาไทย
            thai_font_paths = [
                '/System/Library/Fonts/Thonburi.ttc',  # macOS
                '/usr/share/fonts/truetype/thai/Garuda.ttf',  # Ubuntu
                'C:/Windows/Fonts/tahoma.ttf',  # Windows
            ]
            
            font_registered = False
            for font_path in thai_font_paths:
                if os.path.exists(font_path):
                    try:
                        pdfmetrics.registerFont(TTFont('ThaiFont', font_path))
                        font_registered = True
                        break
                    except:
                        continue
            
            if not font_registered:
                # ใช้ฟอนต์เริ่มต้นถ้าไม่พบฟอนต์ไทย
                self.thai_font = 'Helvetica'
            else:
                self.thai_font = 'ThaiFont'
                
        except Exception as e:
            logger.warning("Could not load Thai fonts: %s", e, exc_info=True)
            self.thai_font = 'Helvetica'
    
    def setup_thai_styles(self):
        """ตั้งค่า styles สำหรับภาษาไทย"""
        self.styles = getSampleStyleSheet()
        
        # Title style - หัวเรื่องหลัก
        self.title_style = ParagraphStyle(
            'ThaiTitle',
            parent=self.styles['Heading1'],
            fontName=self.thai_font,
            fontSize=18,
            spaceAfter=20,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#003366'),
            leading=22
        )
        
        # Heading style - หัวข้อย่อย
        self.heading_style = ParagraphStyle(
            'ThaiHeading',
            parent=self.styles['Heading2'],
            fontName=self.thai_font,
            fontSize=14,
            spaceAfter=12,
            spaceBefore=6,
            textColor=colors.HexColor('#003366'),
            leading=18
        )
        
        # Normal style - ข้อความปกติ
        self.normal_style = ParagraphStyle(
            'ThaiNormal',
            parent=self.styles['Normal'],
            fontName=self.thai_font,
            fontSize=11,
            spaceAfter=6,
            leading=14
        )
        
        # Small style - ข้อความเล็ก
        self.small_style = ParagraphStyle(
            'ThaiSmall',
            parent=self.styles['Normal'],
            fontName=self.thai_font,
            fontSize=9,
            spaceAfter=3,
            leading=11
        )
        
        # Company style - ข้อมูลบริษัท
        self.company_style = ParagraphStyle(
            'ThaiCompany',
            parent=self.styles['Normal'],
            fontName=self.thai_font,
            fontSize=10,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#666666'),
            leading=12
        )
    
    def generate_tour_voucher(self, booking):
        """สร้างใบรับรองทัวร์ภาษาไทย"""
        filename = f"tour_voucher_th_{booking.booking_reference}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        filepath = os.path.join(self.output_dir, filename)
        
        doc = SimpleDocTemplate(
            filepath, 
            pagesize=A4,
            topMargin=1*cm,
            bottomMargin=1*cm,
            leftMargin=1.5*cm,
            rightMargin=1.5*cm
        )
        story = []
        
        # หัวเรื่อง
        title = Paragraph("ใบรับรองการสั่งซื้อทัวร์", self.title_style)
        story.append(title)
        
        # ข้อมูลบริษัท
        company_info = Paragraph(
            f"<b>บริษัท:</b> {Config.COMPANY_NAME}<br/>"
            f"{Config.COMPANY_ADDRESS}<br/>"
            f"โทรศัพท์: {Config.COMPANY_PHONE} | อีเมล: {Config.COMPANY_EMAIL}",
            self.company_style
        )
        story.append(company_info)
        story.append(Spacer(1, 15))
        
        # ข้อมูลการจอง
        booking_info = [
            ['วันที่สร้าง:', thai_date_format(datetime.now().date())],
            ['เลขที่อ้างอิง:', booking.booking_reference],
            ['ระยะเวลาเดินทาง:', f"{thai_date_format(booking.traveling_period_start)} ถึง {thai_date_format(booking.traveling_period_end)}"],
            ['ชื่อลูกค้า:', booking.customer.name],
            ['เบอร์โทรศัพท์:', booking.customer.phone],
            ['อีเมล:', booking.customer.email],
            ['จำนวนผู้เดินทาง:', f"{booking.total_pax} คน"],
        ]
        
        # สร้างตารางข้อมูลการจอง
        info_table = Table(booking_info, colWidths=[4*cm, 10*cm])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), self.thai_font),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8f9fa')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTNAME', (0, 0), (0, -1), self.thai_font),
            ('FONTSIZE', (0, 0), (0, -1), 11),
        ]))
        
        story.append(info_table)
        story.append(Spacer(1, 20))
        
        # รายชื่อผู้เดินทาง
        guest_heading = Paragraph("รายชื่อผู้เดินทาง:", self.heading_style)
        story.append(guest_heading)
        
        guests = booking.get_guest_list()
        if guests:
            guest_data = [['ลำดับ', 'ชื่อ-นามสกุล']]
            for i, guest in enumerate(guests, 1):
                guest_data.append([str(i), guest])
            
            guest_table = Table(guest_data, colWidths=[2*cm, 12*cm])
            guest_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), self.thai_font),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003366')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('ALIGN', (1, 1), (1, -1), 'LEFT'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            
            story.append(guest_table)
        else:
            no_guests = Paragraph("ไม่มีรายชื่อผู้เดินทาง", self.normal_style)
            story.append(no_guests)
        
        story.append(Spacer(1, 20))
        
        # สรุปบริการ
        service_heading = Paragraph("สรุปบริการ", self.heading_style)
        story.append(service_heading)
        
        # ตารางบริการ
        service_data = [['ลำดับ', 'วันที่', 'เวลา', 'รายละเอียดบริการ', 'ประเภท/จำนวนคน']]
        
        daily_services = booking.get_daily_services()
        if daily_services:
            for i, service in enumerate(daily_services, 1):
                service_data.append([
                    str(i),
                    service.get('date', ''),
                    service.get('time', ''),
                    service.get('description', ''),
                    service.get('type', '')
                ])
        else:
            service_data.append([
                '1',
                thai_date_format(booking.arrival_date) if booking.arrival_date else '',
                '',
                'บริการทัวร์',
                f'{booking.total_pax} คน'
            ])
        
        service_table = Table(service_data, colWidths=[1.5*cm, 3*cm, 2*cm, 6*cm, 2.5*cm])
        service_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), self.thai_font),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003366')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (3, 1), (3, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
        ]))
        
        story.append(service_table)
        story.append(Spacer(1, 20))
        
        # ข้อมูลเพิ่มเติม
        if booking.internal_note:
            note_heading = Paragraph("หมายเหตุภายใน:", self.heading_style)
            story.append(note_heading)
            notes = Paragraph(booking.internal_note, self.normal_style)
            story.append(notes)
            story.append(Spacer(1, 12))
        
        if booking.flight_info:
            flight_heading = Paragraph("ข้อมูลเที่ยวบิน:", self.heading_style)
            story.append(flight_heading)
            flight = Paragraph(booking.flight_info, self.normal_style)
            story.append(flight)
            story.append(Spacer(1, 12))
        
        # ข้อมูลการเงิน
        if booking.total_amount:
            financial_heading = Paragraph("ข้อมูลการเงิน:", self.heading_style)
            story.append(financial_heading)
            
            amount_thai = thai_currency_to_text(float(booking.total_amount))
            financial_info = f"""
            <b>ราคารวม:</b> {format_thai_currency(booking.total_amount, booking.currency)}<br/>
            <b>ตัวอักษร:</b> {amount_thai}
            """
            financial_para = Paragraph(financial_info, self.normal_style)
            story.append(financial_para)
            story.append(Spacer(1, 15))
        
        # QR Code
        try:
            qr_path = self.qr_generator.generate_voucher_qr(booking)
            if os.path.exists(qr_path):
                # สร้างตารางสำหรับ QR Code และข้อมูล
                qr_data = [[
                    Image(qr_path, width=3*cm, height=3*cm),
                    Paragraph(
                        f"<b>QR Code สำหรับตรวจสอบ</b><br/>"
                        f"เลขที่อ้างอิง: {booking.booking_reference}<br/>"
                        f"สแกนเพื่อตรวจสอบความถูกต้อง",
                        self.small_style
                    )
                ]]
                
                qr_table = Table(qr_data, colWidths=[4*cm, 10*cm])
                qr_table.setStyle(TableStyle([
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('ALIGN', (0, 0), (0, -1), 'CENTER'),
                    ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ]))
                
                story.append(qr_table)
        except Exception as e:
            logger.error("Error adding QR code (tour_voucher_thai): %s", e, exc_info=True)
        
        story.append(Spacer(1, 25))
        
        # ส่วนลงนาม
        signature_heading = Paragraph("การยืนยันและลงนาม", self.heading_style)
        story.append(signature_heading)
        
        signature_data = [
            ['ยืนยันโดย:', 'รับทราบโดย:'],
            ['', ''],
            ['', ''],
            ['_' * 30, '_' * 30],
            [Config.COMPANY_NAME, booking.customer.name],
            [f'วันที่: {thai_date_format(datetime.now().date())}', 'วันที่: ___/___/______']
        ]
        
        signature_table = Table(signature_data, colWidths=[7*cm, 7*cm])
        signature_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), self.thai_font),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('VALIGN', (0, 1), (-1, 2), 'BOTTOM'),  # เว้นที่สำหรับลายเซ็น
            ('LINEBELOW', (0, 3), (-1, 3), 1, colors.black),
        ]))
        
        story.append(signature_table)
        
        # Footer
        story.append(Spacer(1, 15))
        footer = Paragraph(
            f"เอกสารนี้สร้างโดยระบบ {Config.COMPANY_NAME}<br/>"
            f"สร้างเมื่อ: {thai_datetime_format(datetime.now())}",
            self.small_style
        )
        story.append(footer)
        
        # สร้าง PDF
        doc.build(story)
        return filename
    
    def generate_hotel_ro_thai(self, booking):
        """สร้างใบสั่งจองโรงแรมภาษาไทย"""
        filename = f"hotel_ro_th_{booking.booking_reference}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        filepath = os.path.join(self.output_dir, filename)
        
        doc = SimpleDocTemplate(filepath, pagesize=A4)
        story = []
        
        # หัวเรื่อง
        title = Paragraph("ใบสั่งจองโรงแรม", self.title_style)
        story.append(title)
        
        # ข้อมูลบริษัท
        company_info = Paragraph(
            f"<b>เอเจนซี่:</b> {Config.COMPANY_NAME}",
            self.company_style
        )
        story.append(company_info)
        story.append(Spacer(1, 20))
        
        # รายละเอียดการจอง
        details_data = [
            ['เลขที่อ้างอิงเอเจนซี่:', booking.agency_reference or booking.booking_reference],
            ['ชื่อโรงแรม:', booking.hotel_name or 'ไม่ระบุ'],
            ['ชื่อผู้เข้าพัก:', booking.customer.name],
            ['วันที่เช็คอิน:', thai_date_format(booking.arrival_date) if booking.arrival_date else 'ไม่ระบุ'],
            ['วันที่เช็คเอาท์:', thai_date_format(booking.departure_date) if booking.departure_date else 'ไม่ระบุ'],
            ['จำนวนคืน:', str((booking.departure_date - booking.arrival_date).days) if booking.arrival_date and booking.departure_date else 'ไม่ระบุ'],
            ['ประเภทห้อง:', booking.room_type or 'ไม่ระบุ'],
            ['จำนวนผู้เข้าพัก:', f"{booking.total_pax} คน"],
            ['เบอร์ติดต่อ:', booking.customer.phone],
            ['อีเมล:', booking.customer.email],
        ]
        
        details_table = Table(details_data, colWidths=[5*cm, 9*cm])
        details_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), self.thai_font),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        
        story.append(details_table)
        story.append(Spacer(1, 20))
        
        # คำขอพิเศษ
        if booking.special_request:
            special_heading = Paragraph("คำขอพิเศษ:", self.heading_style)
            story.append(special_heading)
            special_text = Paragraph(booking.special_request, self.normal_style)
            story.append(special_text)
            story.append(Spacer(1, 20))
        
        # รายชื่อผู้เข้าพัก
        guest_heading = Paragraph("รายชื่อผู้เข้าพัก:", self.heading_style)
        story.append(guest_heading)
        
        guests = booking.get_guest_list()
        if guests:
            for i, guest in enumerate(guests, 1):
                guest_item = Paragraph(f"{i}. {guest}", self.normal_style)
                story.append(guest_item)
        
        story.append(Spacer(1, 30))
        
        # QR Code
        try:
            qr_path = self.qr_generator.generate_hotel_ro_qr(booking)
            if os.path.exists(qr_path):
                qr_image = Image(qr_path, width=4*cm, height=4*cm)
                story.append(qr_image)
        except Exception as e:
            logger.error("Error adding QR code (hotel_ro_thai): %s", e, exc_info=True)
        
        # Footer
        footer = Paragraph(
            f"สร้างเมื่อ: {thai_datetime_format(datetime.now())}<br/>"
            f"{Config.COMPANY_NAME}<br/>"
            f"{Config.COMPANY_PHONE}",
            self.small_style
        )
        story.append(footer)
        
        # สร้าง PDF
        doc.build(story)
        return filename
    
    def generate_mpv_booking_thai(self, booking):
        """สร้างใบจอง MPV ภาษาไทย"""
        filename = f"mpv_booking_th_{booking.booking_reference}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        filepath = os.path.join(self.output_dir, filename)
        
        doc = SimpleDocTemplate(filepath, pagesize=A4)
        story = []
        
        # หัวเรื่อง
        title = Paragraph("ใบยืนยันการจองรถรับส่ง", self.title_style)
        story.append(title)
        
        # ข้อมูลบริษัท
        company_info = Paragraph(
            f"<b>บริษัทรถรับส่ง:</b> {Config.COMPANY_NAME}",
            self.company_style
        )
        story.append(company_info)
        story.append(Spacer(1, 20))
        
        # รายละเอียดการจอง
        details_data = [
            ['เลขที่การจอง:', booking.booking_reference],
            ['ชื่อลูกค้า:', booking.customer.name],
            ['ประเภทรถ:', booking.vehicle_type or 'ไม่ระบุ'],
            ['จุดรับ:', booking.pickup_point or 'ไม่ระบุ'],
            ['ปลายทาง:', booking.destination or 'ไม่ระบุ'],
            ['วันที่รับ:', thai_date_format(booking.arrival_date) if booking.arrival_date else 'ไม่ระบุ'],
            ['เวลารับ:', booking.pickup_time.strftime('%H:%M น.') if booking.pickup_time else 'ไม่ระบุ'],
            ['จำนวนผู้โดยสาร:', f"{booking.total_pax} คน"],
            ['เบอร์ติดต่อ:', booking.customer.phone],
            ['อีเมล:', booking.customer.email],
            ['ราคารวม:', format_thai_currency(booking.total_amount, booking.currency) if booking.total_amount else 'ไม่ระบุ'],
        ]
        
        details_table = Table(details_data, colWidths=[5*cm, 9*cm])
        details_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), self.thai_font),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        
        story.append(details_table)
        story.append(Spacer(1, 20))
        
        # รายชื่อผู้โดยสาร
        passenger_heading = Paragraph("รายชื่อผู้โดยสาร:", self.heading_style)
        story.append(passenger_heading)
        
        guests = booking.get_guest_list()
        if guests:
            for i, guest in enumerate(guests, 1):
                guest_item = Paragraph(f"{i}. {guest}", self.normal_style)
                story.append(guest_item)
        
        story.append(Spacer(1, 20))
        
        # เงื่อนไขและข้อตกลง
        terms_heading = Paragraph("เงื่อนไขและข้อตกลง:", self.heading_style)
        story.append(terms_heading)
        
        terms_text = """
        1. กรุณาเตรียมตัวพร้อม 15 นาทีก่อนเวลารับ<br/>
        2. คนขับจะรอสูงสุด 30 นาทีที่จุดรับ<br/>
        3. การเปลี่ยนแปลงต้องแจ้งล่วงหน้าอย่างน้อย 24 ชั่วโมง<br/>
        4. นำนโยบายการยกเลิกตามเงื่อนไขของบริษัท<br/>
        5. การแวะจุดเพิ่มเติมอาจมีค่าใช้จ่ายเพิ่ม
        """
        
        terms = Paragraph(terms_text, self.normal_style)
        story.append(terms)
        story.append(Spacer(1, 20))
        
        # QR Code
        try:
            qr_path = self.qr_generator.generate_mpv_qr(booking)
            if os.path.exists(qr_path):
                qr_image = Image(qr_path, width=4*cm, height=4*cm)
                story.append(qr_image)
        except Exception as e:
            logger.error("Error adding QR code (mpv_booking_thai): %s", e, exc_info=True)
        
        # Footer
        footer = Paragraph(
            f"สร้างเมื่อ: {thai_datetime_format(datetime.now())}<br/>"
            f"{Config.COMPANY_NAME}<br/>"
            f"{Config.COMPANY_PHONE}",
            self.small_style
        )
        story.append(footer)
        
        # สร้าง PDF
        doc.build(story)
        return filename
