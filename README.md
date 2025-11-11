# ระบบจัดการใบบัตรทัวร์ (Tour Voucher Management System)

ระบบจัดการใบบัตรทัวร์แบบครบวงจร พัฒนาด้วย Flask และรองรับภาษาไทย พร้อมการเชื่อมต่อกับ Invoice Ninja API

## ✨ คุณสมบัติหลัก

### � จัดการใบบัตร
- สร้างใบบัตรทัวร์อัตโนมัติ
- ใบบัตร PDF ภาษาไทยที่สวยงาม
- QR Code สำหรับการตรวจสอบ
- การติดตามสถานะใบบัตร

### 📅 จัดการการจอง
- ระบบจองที่ใช้งานง่าย
- ติดตามสถานะการจอง
- ประวัติการจองทั้งหมด
- การอัปเดตสถานะแบบเรียลไทม์

### 👥 จัดการลูกค้า
- ข้อมูลลูกค้าแบบครบถ้วน
- ประวัติการจองของลูกค้า
- ระบบค้นหาและกรอง

### 🌐 รองรับหลายภาษา
- ภาษาไทย (เริ่มต้น)
- ภาษาอังกฤษ
- การเปลี่ยนภาษาแบบเรียลไทม์

### 💰 เชื่อมต่อ Invoice Ninja
- สร้างใบแจ้งหนี้อัตโนมัติ
- ติดตามการชำระเงิน
- รายงานการเงิน

### 📊 แดชบอร์ดและรายงาน
- สถิติการจองแบบเรียลไทม์
- รายงาน PDF ภาษาไทย
- กราฟและแผนภูมิ

## 🛠️ เทคโนโลยี

- **Backend**: Flask, Python 3.8+
- **Database**: MySQL
- **Frontend**: Bootstrap 5, HTML5, CSS3
- **PDF Generation**: ReportLab
- **QR Codes**: qrcode library
- **API Integration**: Invoice Ninja REST API
- **Email**: SMTP integration

## 🧾 Logging & Observability

โค้ดได้ย้ายจาก `print()` ไปสู่ระบบ logging แบบรวมศูนย์แล้ว (ดูไฟล์ `utils/logging_config.py`).

### ตั้งค่า Log Level
กำหนดระดับ log ผ่าน environment variable `LOG_LEVEL` (ค่าเริ่มต้น: INFO)

รองรับค่า: DEBUG, INFO, WARNING, ERROR, CRITICAL

ตัวอย่าง:
```bash
export LOG_LEVEL=DEBUG
python run.py
```

รูปแบบบรรทัด log:
```
YYYY-MM-DD HH:MM:SS,mmm | LEVEL    | package.module | message
```

### การกำหนดระดับที่เหมาะสม
- DEBUG: รายละเอียดการโหลดฟอนต์ / caching / sanitized HTML
- INFO: เหตุการณ์ปกติ (สร้างไฟล์ PDF, ส่งอีเมลสำเร็จ, ดาวน์โหลดฟอนต์)
- WARNING: ปัญหาไม่ร้ายแรง (ฟอนต์ fallback, ข้อผิดพลาดค้นหา Invoice Ninja ที่ไม่ critical)
- ERROR: ความล้มเหลวของฟังก์ชันหลัก (ส่งอีเมลล้มเหลว, สร้าง PDF ล้มเหลว)

## 🔤 Thai Font System & Fallback

ระบบจะพยายามใช้ฟอนต์ภาษาไทยคุณภาพสูง (NotoSansThai) อัตโนมัติ:
1. ตรวจหาไฟล์ใน `static/fonts/` หรือ `fonts/`
2. ถ้าไม่พบและเปิดอนุญาต download จะดาวน์โหลด `NotoSansThai-Regular.ttf` และ `NotoSansThai-Bold.ttf`
3. ตรวจสอบขนาดไฟล์และคำนวณ sha256 ยืนยันความสมบูรณ์
4. Cache รายการฟอนต์ในหน่วยความจำ (หลีกเลี่ยง I/O ซ้ำ)
5. ถ้าทุกอย่างล้มเหลว → fallback ไปยัง Thonburi / DejaVuSans / Helvetica ตามลำดับ

ไฟล์โค้ดหลัก: `services/font_utils.py` (ฟังก์ชัน `ensure_thai_fonts`) และการลงทะเบียนใน `services/pdf_generator.py`.

### บังคับดาวน์โหลดใหม่
ลบไฟล์ใน `static/fonts/` แล้วรันแอปใหม่ (cache ในโปรเซสจะรีเซ็ตเมื่อ restart):
```bash
rm -f static/fonts/NotoSansThai-*.ttf
export LOG_LEVEL=DEBUG
python run.py
```
จะเห็น log: `Downloaded font NotoSansThai-Regular.ttf ...`

### ปัญหาที่พบบ่อย
| อาการ | สาเหตุ | แนวทางแก้ |
|-------|--------|-----------|
| ตัวอักษรไทยเป็นสี่เหลี่ยม | ฟอนต์ไม่ถูกโหลด | ตรวจ log WARNING/ERROR และสิทธิ์ไฟล์ |
| PDF ไทยบางส่วนใช้ font อื่น | ฟอนต์หลักไม่ครอบคลุม glyph | ตรวจ fallback chain ใน log |
| ดาวน์โหลดฟอนต์ช้า | Network ช้า / GitHub timeout | วางไฟล์ฟอนต์ไว้ล่วงหน้าใน `static/fonts/` |

## 🧪 Sanitized HTML ใน PDF
เพื่อความปลอดภัย `_clean_simple_html` ใน `pdf_generator` จะ:
- อนุญาตเฉพาะแท็ก: b, strong, i, em, u, br, p, ul, ol, li
- ตัด script/style/iframe/object/embed/meta/link
- ลบ event handlers (`onclick="..."` เป็นต้น)
- ป้องกัน `javascript:` และ `data:` URI
หากต้องเพิ่มแท็ก ให้แก้ชุด `allowed` ในเมธอดนั้นอย่างระมัดระวัง


## 📋 Requirements

### System Requirements
- Python 3.8+
- MySQL 5.7+ or MariaDB 10.2+
- 1GB RAM minimum
- 500MB disk space

### Python Dependencies
See `requirements.txt` for complete list:
- Flask 2.3.3
- Flask-SQLAlchemy 3.0.5
- Flask-Login 0.6.3
- MySQL-connector-python 8.1.0
- ReportLab 4.0.4
- qrcode[pil] 7.4.2

## 🚀 Quick Start

### 1. Clone & Setup
```bash
cd /Applications/python/voucher-ro_v1.0
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Database Setup
```sql
-- Create MySQL database
CREATE DATABASE tour_voucher_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'voucher_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON tour_voucher_db.* TO 'voucher_user'@'localhost';
FLUSH PRIVILEGES;
```

### 3. Environment Configuration
Copy `.env` file and update with your settings:
```bash
cp .env .env.local
# Edit .env.local with your database and API credentials
```

### 4. Initialize Database
```bash
python run.py
# This will create all tables and an admin user
```

### 5. Run Application
```bash
python run.py
# Access at http://localhost:5000
```

**Default Admin Login:**
- Username: `admin`
- Password: `admin123`

## 📁 Project Structure

```
voucher-ro_v1.0/
├── app.py                 # Flask application factory
├── run.py                 # Application runner
├── config.py              # Configuration settings
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables
├── models/                # Database models
│   ├── user.py           # User authentication
│   ├── customer.py       # Customer management
│   └── booking.py        # Booking system
├── routes/                # Application routes
│   ├── auth.py           # Authentication routes
│   ├── dashboard.py      # Dashboard & analytics
│   ├── booking.py        # Booking management
│   ├── voucher.py        # Voucher generation
│   └── api.py            # REST API endpoints
├── services/              # Business logic
│   ├── invoice_ninja.py  # Invoice Ninja integration
│   ├── pdf_generator.py  # PDF generation
│   ├── qr_generator.py   # QR code generation
│   └── email_service.py  # Email functionality
├── utils/                 # Utility functions
│   └── booking_utils.py  # Booking helpers
├── templates/             # HTML templates
│   ├── base.html         # Base template
│   ├── auth/             # Authentication pages
│   ├── dashboard/        # Dashboard pages
│   ├── booking/          # Booking management
│   └── voucher/          # Voucher pages
└── static/               # Static files
    ├── generated/        # Generated PDFs
    └── qr_codes/         # QR code images
```

## � PDF Font Configuration

Environment flags:


Run example:
```bash
PDF_DISABLE_FONT_SUBSETTING=true PDF_PREDOWNLOAD_FONTS=true python run.py
```

To re-download fonts manually:
```bash
rm -f static/fonts/NotoSansThai-*.ttf
PDF_PREDOWNLOAD_FONTS=true python run.py
```

Tests include `test_pdf_no_square_glyphs.py` to ensure no square/bullet placeholder glyphs remain.

## �🔌 API Integration

## PDF Generation
... existing content ...

### PDF Configuration Environment Variables
The PDF layer can be tuned at runtime using the following environment variables (all optional). Boolean values accept 1/0, true/false, yes/no (case‑insensitive).

| Variable | Default | Description |
|----------|---------|-------------|
| PDF_DISABLE_FONT_SUBSETTING | false | When true, disable ReportLab font subsetting to retain full glyph sets (larger file size, safer for Thai/CJK). |
| PDF_PREDOWNLOAD_FONTS | true | Attempt to download required Noto fonts on startup. |
| PDF_FORCE_EMBED_FONTS | false | Forces embedding of all fallback fonts by adding invisible glyph usage to guarantee inclusion. |
| PDF_FALLBACK_FONTS | ThaiFont,NotoSansThai,NotoSansThai-Regular,DejaVuSans,Helvetica,Times-Roman | Ordered list scanned when selecting a font for Thai/CJK text blocks. |
| PDF_FONT_DIR | (unset) | Directory scanned for all .ttf files to auto‑register (names derived from filename). |
| PDF_ENABLE_COMPRESSION | true | Toggle ReportLab page compression (affects file size). |
| PDF_QR_CACHE_TTL | 0 | Seconds to cache generated QR PNGs (0 = no cache). |
| PDF_TABLE_ZEBRA | true | Enable zebra striping for voucher/service tables. |
| PDF_TERMS_LIST_STYLE | number | Terms bullet style: number | dash | none. |
| PDF_ALLOWED_TAGS | b,strong,i,em,u,br,p,ul,ol,li | Override sanitization whitelist (intersection with safe superset). |

Example (.env):
```
PDF_DISABLE_FONT_SUBSETTING=true
PDF_FORCE_EMBED_FONTS=true
PDF_FALLBACK_FONTS=ThaiFont,NotoSansThai,DejaVuSans
PDF_TABLE_ZEBRA=false
PDF_TERMS_LIST_STYLE=dash
PDF_ALLOWED_TAGS=b,strong,br,p
PDF_QR_CACHE_TTL=86400
```

### QR Cache Cleanup
If QR caching is enabled (`PDF_QR_CACHE_TTL` > 0), PNG files accumulate under `static/qr_codes`.
Utility script: `python -m utils.qr_cache_cleanup`.

Commands:
```
python -m utils.qr_cache_cleanup --dry-run   # show what would be removed
python -m utils.qr_cache_cleanup            # delete expired files
python -m utils.qr_cache_cleanup --ttl 3600 # override TTL for this run
```
Example cron (daily 02:00):
```
0 2 * * * /usr/bin/python /path/to/app/utils/qr_cache_cleanup.py >> /var/log/qr_cleanup.log 2>&1
```
TTL = 0 means no caching (script removes nothing).


### Font Fallback Logic
Whenever Thai (U+0E00–U+0E7F) or basic CJK (U+4E00–U+9FFF) characters are detected in a paragraph, the generator attempts to switch to the first registered font in `PDF_FALLBACK_FONTS` to ensure glyph coverage.

#### Detailed Font Strategy
Flow:
1. Register built‑in / downloaded fonts (Thai, optionally external directory) at startup.
2. For each paragraph / text block: scan for Thai or CJK codepoints.
3. If found, iterate `PDF_FALLBACK_FONTS` in order; first registered name wins.
4. If none found and Thai only, fall back to `NotoSansThai` if registered.
5. If still none, stay with base font (may produce missing glyphs → visible as tofu; covered by tests).

You can add a CJK capable font by mounting a directory and setting:
```
PDF_FONT_DIR=/opt/fonts
PDF_FALLBACK_FONTS=NotoSansCJKsc-Regular,NotoSansThai,DejaVuSans,Helvetica
```
Place `NotoSansCJKsc-Regular.ttf` inside `/opt/fonts`.

Utility `utils/pdf_fonts.py` centralizes selection logic so both voucher and simple generators stay consistent.

### Multi‑Script (Thai + CJK + Latin) Support
Tests (`test_multiscript_fonts.py`) validate that a single PDF can contain Thai + Chinese (or other CJK) + Latin text without tofu squares. The test logic now:
* SKIP (not fail) automatically if no CJK font is registered.
* ASSERT presence of Thai + at least one Han character + Latin tokens when a CJK font is present.

Quick setup:
1. Download a CJK font (examples):
  * Noto Sans CJK SC: `NotoSansCJKsc-Regular.otf`
  * Noto Sans CJK TC: `NotoSansCJKtc-Regular.otf`
  * Source Han Sans (Adobe) variant
2. Place the file into a directory, e.g. `fonts/` at project root.
3. Export environment variables BEFORE running tests:
```
export PDF_FONT_DIR=$(pwd)/fonts
export PDF_FALLBACK_FONTS=NotoSansCJKsc-Regular,NotoSansThai,DejaVuSans,Helvetica
export PDF_DISABLE_FONT_SUBSETTING=true      # (optional but improves reliability of glyph extraction)
export PDF_FORCE_EMBED_FONTS=true            # (optional; ensures font fully embedded)
```
4. Run only the multi‑script test:
```
make multiscript-check
```
5. (Optional) Inspect fonts actually embedded:
```
python -m utils.font_inventory static/generated/*.pdf | grep Font
```

Troubleshooting:
| Symptom | Cause | Fix |
|---------|-------|-----|
| Test skipped | No CJK font registered | Verify `PDF_FONT_DIR` & filename ends with .ttf/.otf |
| Chinese glyphs missing | Subsetting removed glyphs | Disable subsetting + force embed |
| File size large | Full embedding of large CJK font | Re‑enable subsetting or use a subset font |
| Still tofu squares | Wrong font family (no Han glyphs) | Use NotoSansCJK or SourceHan Sans |

CI Hint: If you want the multi‑script test to always run in CI, add the font to the repo or fetch it in a setup step, then export the env vars in the CI job.

### Performance Benchmarking
Script: `scripts/pdf_benchmark.py`
Measures combinations of three toggles:
* `PDF_ENABLE_COMPRESSION`
* `PDF_TABLE_ZEBRA`
* `PDF_FORCE_EMBED_FONTS`

Metrics per combination (voucher & simple generators): mean, median, p95, p99 time (ms) and average file size (bytes).

Run quick benchmark (3 runs each):
```
python scripts/pdf_benchmark.py --runs 3
```
Artifacts:
```
scripts/benchmark_output/pdf_benchmark.csv
scripts/benchmark_output/pdf_benchmark.md
```

Makefile target:
```
make benchmark      # runs with --runs 3
```

For higher statistical confidence (≥5 runs):
```
python scripts/pdf_benchmark.py --runs 10
```

### Font Inventory Utility
Inspect which font resource names appear inside a generated PDF (heuristic):
```
python -m utils.font_inventory static/generated/your_file.pdf
```
Useful to confirm fallback / embedding decisions.

### Developer Workflow Enhancements
Pre-commit hooks included (.pre-commit-config.yaml): black, ruff (auto-fix), and a fast pytest subset.
Install:
```
pip install pre-commit
pre-commit install
```
Run manually on all files:
```
pre-commit run --all-files
```

### Sanitization
Simple HTML sanitizer removes disallowed tags/attributes, strips event handlers, and normalizes newlines to `<br/>`. To allow an additional tag, add it to `PDF_ALLOWED_TAGS` (must still be in the internal safe set).

### Invoice Ninja Setup
1. Install Invoice Ninja or use hosted version
2. Generate API token in Settings > Account Management
3. Update `.env` with your Invoice Ninja URL and token

### API Endpoints
- `POST /api/customers` - Create customer
- `POST /api/bookings` - Create booking
- `POST /api/invoice-ninja/quote` - Create quote
- `POST /api/invoice-ninja/invoice` - Create invoice

## 📊 Usage Guide

### Creating a Tour Voucher
1. **Login** to admin dashboard
2. **Create Customer** (if new)
3. **Create Booking** with tour type
4. **Generate Quote/Invoice** via Invoice Ninja
5. **Generate Tour Voucher PDF** with QR code
6. **Email or Print** voucher

### Hotel Reservation Order
1. Create booking with type "hotel"
2. Fill hotel details (name, dates, room type)
3. Generate Hotel RO PDF
4. Send to hotel for confirmation

### MPV Transport Booking
1. Create booking with type "transport"
2. Set pickup/destination details
3. Generate MPV booking PDF
4. Confirm with transport provider

## 🎨 Customization

### Company Branding
Update `config.py` with your company details:
```python
COMPANY_NAME = "Your Travel Company"
COMPANY_ADDRESS = "Your Address"
COMPANY_PHONE = "+66-xxx-xxx-xxx"
COMPANY_EMAIL = "info@yourcompany.com"
```

### PDF Templates
Modify `services/pdf_generator.py` to customize:
- Layout and styling
- Company logos
- Additional fields
- QR code positioning

### Email Templates
Edit `services/email_service.py` for:
- Custom email content
- HTML templates
- Attachment handling

## 🚀 Deployment

### Production Setup
1. Use production MySQL database
2. Set `FLASK_ENV=production`
3. Configure reverse proxy (Nginx/Apache)
4. Use WSGI server (Gunicorn/uWSGI)
5. Set up SSL certificates

### Docker Deployment
```bash
# Build image
docker build -t tour-voucher-system .

# Run with environment variables
docker run -p 5000:5000 --env-file .env tour-voucher-system
```

## 🔒 Security

- Password hashing with Werkzeug
- Session management with Flask-Login
- SQL injection prevention with SQLAlchemy
- CSRF protection with Flask-WTF
- Environment variable configuration

## 📝 API Documentation

### Authentication
All API endpoints require authentication via session cookies or API tokens.

### Booking API
```bash
# Create booking
curl -X POST http://localhost:5000/api/bookings \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": 1,
    "booking_type": "tour",
    "total_amount": 1500.00,
    "guest_list": ["John Doe", "Jane Doe"]
  }'
```

### Invoice Ninja Integration
```bash
# Create quote
curl -X POST http://localhost:5000/api/invoice-ninja/quote \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": 1,
    "items": [{
      "product_key": "TOUR001",
      "description": "Bangkok City Tour",
      "cost": 1500.00,
      "quantity": 1
    }]
  }'
```

## 🐛 Troubleshooting

### Common Issues

1. **Database Connection Error**
   - Check MySQL service is running
   - Verify credentials in `.env`
   - Ensure database exists

2. **PDF Generation Failed**
   - Install ReportLab: `pip install reportlab`
   - Check file permissions in `static/generated/`

3. **QR Code Error**
   - Install qrcode: `pip install qrcode[pil]`
   - Verify PIL/Pillow installation

4. **Email Sending Failed**
   - Check SMTP settings in `.env`
   - Verify email credentials
   - Test with `EmailService.test_email_connection()`

### Debug Mode
Run with debug enabled:
```bash
export FLASK_ENV=development
python run.py
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/new-feature`)
3. Commit changes (`git commit -am 'Add new feature'`)
4. Push to branch (`git push origin feature/new-feature`)
5. Create Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📞 Support

For support and questions:
- Email: support@dhakulchan.com
- Phone: +66-xxx-xxx-xxx

## 🙏 Acknowledgments

- Flask community for excellent framework
- Invoice Ninja for API integration
- Bootstrap team for responsive UI components
- ReportLab for PDF generation capabilities

---

**Built with ❤️ for the tourism industry**
# voucher-system1
# voucher-system1
# voucher-system1
# voucher-system1
# voucher-system1
# voucher-system1
