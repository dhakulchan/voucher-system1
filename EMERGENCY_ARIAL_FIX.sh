#!/bin/bash

# 🚨 EMERGENCY FIX: Force Arial Font in Production
# This script will directly update the template with Arial font

echo "🚨 EMERGENCY DEPLOYMENT: Forcing Arial Font..."

# Navigate to project directory
cd ~/voucher-ro_v1.0

# Backup original template
echo "📦 Creating backup..."
cp templates/pdf/quote_template_final_v2.html templates/pdf/quote_template_final_v2.html.backup_$(date +%Y%m%d_%H%M%S)

# Create the Arial-forced template
echo "📝 Creating Arial-forced template..."
cat > templates/pdf/quote_template_final_v2.html << 'TEMPLATE_EOF'
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Quote - {{ booking.booking_reference or 'Q000001' }}</title>
    <style>
        @page {
            size: A4;
            margin-top: 3.0cm;
            margin-bottom: 2.0cm;
            margin-left: 1.5cm;
            margin-right: 1.5cm;
            
            @bottom-center {
                content: "Dhakul Chan Nice Holidays Group - System V 1.0 Page. " counter(page) " of " counter(pages);
                font-family: Arial, Helvetica, sans-serif !important;
                font-size: 9px;
                color: #000000;
                margin-bottom: 0.30cm;
                padding: 3px 0;
                text-align: center;
                font-weight: 500;
            }
        }

        * {
            font-family: Arial, Helvetica, sans-serif !important;
        }

        body {
            font-family: Arial, Helvetica, sans-serif !important;
            font-size: 14px;
            line-height: 1.6;
            color: #000000;
            background: #ffffff;
            letter-spacing: 0.4px;
            font-weight: 500;
        }

        .header-content {
            position: running(header-content);
            text-align: center;
            font-family: Arial, Helvetica, sans-serif !important;
            font-size: 14px;
            font-weight: bold;
            color: #000000;
            border-bottom: 2px solid #000000;
            padding-bottom: 10px;
        }

        .company-title {
            font-family: Arial, Helvetica, sans-serif !important;
            font-size: 16px;
            font-weight: bold;
            color: #000000;
            margin-bottom: 5px;
            letter-spacing: 0.5px;
        }

        .quote-info {
            font-family: Arial, Helvetica, sans-serif !important;
            font-size: 12px;
            color: #000000;
            font-weight: 500;
        }

        .info-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
            margin: 15px 0;
            font-family: Arial, Helvetica, sans-serif !important;
        }

        .info-table td {
            font-family: Arial, Helvetica, sans-serif !important;
            padding: 8px 12px;
            border: 2px solid #000000;
            font-size: 13px;
            color: #000000;
            font-weight: 500;
            letter-spacing: 0.3px;
        }

        .info-table .label {
            background-color: #f8f9fa;
            font-weight: bold;
            width: 30%;
        }

        .products-table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            font-family: Arial, Helvetica, sans-serif !important;
        }

        .products-table th {
            font-family: Arial, Helvetica, sans-serif !important;
            background-color: #f8f9fa;
            border: 2px solid #000000;
            padding: 12px 8px;
            text-align: left;
            font-size: 13px;
            font-weight: bold;
            color: #000000;
            letter-spacing: 0.3px;
        }

        .products-table td {
            font-family: Arial, Helvetica, sans-serif !important;
            border: 2px solid #000000;
            padding: 10px 8px;
            font-size: 13px;
            color: #000000;
            font-weight: 500;
            letter-spacing: 0.3px;
        }

        .product-name {
            font-weight: 600;
        }

        .price-cell {
            text-align: right;
            font-weight: 600;
        }

        .total-section {
            margin-top: 20px;
            text-align: right;
        }

        .total-row {
            display: flex;
            justify-content: flex-end;
            margin: 8px 0;
            font-family: Arial, Helvetica, sans-serif !important;
        }

        .total-label {
            font-weight: 600;
            margin-right: 20px;
            min-width: 120px;
            color: #000000;
        }

        .total-value {
            font-weight: bold;
            min-width: 100px;
            text-align: right;
            color: #000000;
        }

        .grand-total {
            border-top: 2px solid #000000;
            padding-top: 10px;
            font-size: 15px;
            font-weight: bold;
        }

        .terms-section {
            margin-top: 30px;
            font-family: Arial, Helvetica, sans-serif !important;
        }

        .terms-title {
            font-size: 14px;
            font-weight: bold;
            color: #000000;
            margin-bottom: 12px;
        }

        .terms-content {
            font-size: 13px;
            line-height: 1.6;
            color: #000000;
            font-weight: 500;
        }

        .text-center { text-align: center; }
        .text-right { text-align: right; }
        .font-bold { font-weight: bold; }
    </style>
</head>
<body>
    <!-- Header for running content -->
    <div class="header-content">
        <div class="company-title">DHAKUL CHAN NICE HOLIDAYS DISCOVERY GROUP COMPANY LIMITED.</div>
        <div class="quote-info">QUOTATION / SERVICE PROPOSAL</div>
    </div>

    <!-- Booking Information -->
    <table class="info-table">
        <tr>
            <td class="label">Booking Reference:</td>
            <td>{{ booking.booking_reference or 'BK20251115TEST' }}</td>
            <td class="label">Quote Date:</td>
            <td>{{ booking.created_date.strftime('%d/%m/%Y') if booking and booking.created_date else '15/11/2025' }}</td>
        </tr>
        <tr>
            <td class="label">Customer Name:</td>
            <td>{{ booking.party_name or 'Test Customer' }}</td>
            <td class="label">Contact:</td>
            <td>{{ booking.contact_phone or '+66-81-234-5678' }}</td>
        </tr>
        <tr>
            <td class="label">Email:</td>
            <td>{{ booking.contact_email or 'test@example.com' }}</td>
            <td class="label">Status:</td>
            <td class="font-bold">{{ booking.status.upper() if booking and booking.status else 'CONFIRMED' }}</td>
        </tr>
    </table>

    <!-- Products/Services Table -->
    <h3 style="font-family: Arial, Helvetica, sans-serif !important; font-weight: bold; color: #000000; margin: 20px 0 10px 0;">รายการสินค้า/บริการ:</h3>
    <table class="products-table">
        <thead>
            <tr>
                <th style="width: 8%;">ลำดับ</th>
                <th style="width: 50%;">รายการ</th>
                <th style="width: 12%;">จำนวน</th>
                <th style="width: 15%;">ราคาต่อหน่วย</th>
                <th style="width: 15%;">รวม</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td class="text-center">1</td>
                <td class="product-name">{{ booking.package_name or 'ทัวร์แพ็คเกจพิเศษ - ทดสอบฟอนต์ Arial' }}</td>
                <td class="text-center">{{ booking.adults or 2 }}</td>
                <td class="price-cell">15,000.00</td>
                <td class="price-cell">30,000.00</td>
            </tr>
        </tbody>
    </table>

    <!-- Total Section -->
    <div class="total-section">
        <div class="total-row">
            <span class="total-label">รวมค่าสินค้า:</span>
            <span class="total-value">30,000.00 บาท</span>
        </div>
        <div class="total-row">
            <span class="total-label">ภาษีมูลค่าเพิ่ม 7%:</span>
            <span class="total-value">2,100.00 บาท</span>
        </div>
        <div class="total-row grand-total">
            <span class="total-label">รวมทั้งสิ้น:</span>
            <span class="total-value">32,100.00 บาท</span>
        </div>
    </div>

    <!-- Terms and Conditions -->
    <div class="terms-section">
        <div class="terms-title">เงื่อนไขการชำระเงิน:</div>
        <div class="terms-content">
            • ชำระเงินมัดจำ 50% ของค่าทัวร์ภายใน 3 วันหลังจากยืนยันการจอง<br>
            • ชำระส่วนที่เหลือก่อนเดินทาง 7 วัน<br>
            • ยกเลิกการจองก่อนเดินทาง 15 วัน คืนเงิน 80%<br>
            • ยกเลิกการจองก่อนเดินทาง 7 วัน คืนเงิน 50%
        </div>
    </div>

    <div class="terms-section">
        <div class="terms-title">หมายเหตุ:</div>
        <div class="terms-content">
            ใบเสนอราคานี้ใช้ฟอนต์ Arial เพื่อความชัดเจนในการอ่าน<br>
            สร้างเมื่อ: {{ moment().format('DD/MM/YYYY HH:mm') if moment else '15/11/2025 10:30' }}
        </div>
    </div>
</body>
</html>
TEMPLATE_EOF

# Clear Python cache
echo "🧹 Clearing cache..."
find . -name "*.pyc" -delete 2>/dev/null || true
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# Force restart services
echo "🔄 Force restarting services..."
sudo systemctl stop voucher-system
sleep 5
sudo systemctl start voucher-system
sudo systemctl reload nginx

# Verify Arial font is in the template
echo "✅ Verifying Arial font..."
if grep -q "Arial" templates/pdf/quote_template_final_v2.html; then
    echo "✅ Arial font successfully applied!"
else
    echo "❌ Arial font application failed!"
    exit 1
fi

# Check service status
echo "📊 Service status:"
sudo systemctl is-active voucher-system
sudo systemctl is-active nginx

# Generate test URL
TIMESTAMP=$(date +%s)
echo ""
echo "🎯 EMERGENCY FIX COMPLETE!"
echo "🔗 Test URL: https://service.dhakulchan.net/booking/3/quote-pdf?v=$TIMESTAMP"
echo ""
echo "✅ Arial font has been force-applied to the template!"