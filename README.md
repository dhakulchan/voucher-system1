# Thai Font Fix - Ready for Deployment

## 🎯 Problem
Quote PDFs showing Thai text in blurry Arial font instead of clear Thai fonts.

## ✅ Solution
New template using Tahoma font with excellent Thai character support.

## 📁 Files Included
- `quote_template_system_fonts.html` - Main template to deploy
- `quote_template_final_thai_fix.html` - Alternative version
- `quote_template_emergency_thai.html` - Backup template
- `server_deploy.sh` - Automated deployment script
- `MANUAL_DEPLOYMENT_GUIDE.txt` - Detailed instructions

## 🚀 Quick Deployment

### Option 1: Automated (if you have server access)
1. Upload all files to server
2. SSH to server: `ssh ubuntu@52.220.243.237`
3. Run: `bash server_deploy.sh`

### Option 2: Manual File Replace
1. Upload `quote_template_system_fonts.html` to server
2. Replace file at: `/var/www/html/templates/pdf/quote_template_system_fonts.html`
3. Restart services: `sudo systemctl restart gunicorn nginx`

## 🔗 Test Result
https://service.dhakulchan.net/booking/3/quote-pdf

## ✅ Expected Improvement
Thai text will be sharp and clear with Tahoma font instead of blurry Arial.
