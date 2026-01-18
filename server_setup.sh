#!/bin/bash
#═══════════════════════════════════════════════════════════════════════════
# AWS Lightsail Complete Setup Script
# For: booking-dhakulchan-prod (Debian 12)
# Domain: https://booking.dhakulchan.net
# 
# Run this script on the fresh AWS Lightsail instance
# Usage: bash server_setup.sh
#═══════════════════════════════════════════════════════════════════════════

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║     AWS Lightsail Complete Server Setup                   ║${NC}"
echo -e "${CYAN}║     Booking Management System                              ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo -e "${RED}❌ Don't run as root! Run as admin user.${NC}" 
   exit 1
fi

echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}📦 Step 1: Update System${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
sudo apt update
sudo apt upgrade -y

echo -e "\n${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}🔧 Step 2: Install System Dependencies${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
sudo apt install -y \
    python3.11 python3.11-venv python3-pip \
    mariadb-server mariadb-client \
    nginx \
    git curl wget vim nano \
    build-essential pkg-config \
    libmariadb-dev libmariadb-dev-compat python3-dev \
    libcairo2 libpango-1.0-0 libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 libffi-dev shared-mime-info \
    certbot python3-certbot-nginx \
    ufw

echo -e "\n${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}🗃️ Step 3: Setup MariaDB Database${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
sudo systemctl enable mariadb
sudo systemctl start mariadb

# Create database and user
sudo mysql -e "CREATE DATABASE IF NOT EXISTS voucher_enhanced CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
sudo mysql -e "CREATE USER IF NOT EXISTS 'voucher_user'@'localhost' IDENTIFIED BY 'VoucherSecure2026!';"
sudo mysql -e "GRANT ALL PRIVILEGES ON voucher_enhanced.* TO 'voucher_user'@'localhost';"
sudo mysql -e "FLUSH PRIVILEGES;"

echo -e "${GREEN}✅ Database created: voucher_enhanced${NC}"

echo -e "\n${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}📁 Step 4: Setup Application Directory${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
sudo mkdir -p /var/www/booking
sudo chown admin:admin /var/www/booking
cd /var/www/booking

echo -e "\n${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}📥 Step 5: Clone Repository from GitHub${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
git clone https://github.com/dhakulchan/voucher-system1.git .

echo -e "\n${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}🐍 Step 6: Setup Python Virtual Environment${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo -e "\n${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}📝 Step 7: Setup Environment Variables${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
cp deploy/.env.production .env
echo -e "${YELLOW}⚠️  Remember to update SECRET_KEY and other sensitive values in .env${NC}"

echo -e "\n${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}📊 Step 8: Initialize Database${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
source venv/bin/activate
python run.py &
FLASK_PID=$!
sleep 10
kill $FLASK_PID || true
echo -e "${GREEN}✅ Database tables initialized${NC}"

echo -e "\n${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}📜 Step 9: Setup Systemd Service${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
sudo mkdir -p /var/log/booking-system
sudo chown admin:admin /var/log/booking-system
sudo cp systemd/booking-system.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable booking-system
sudo systemctl start booking-system

echo -e "\n${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}🌐 Step 10: Setup Nginx${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
sudo cp nginx/booking.dhakulchan.net.conf /etc/nginx/sites-available/booking.dhakulchan.net
sudo ln -sf /etc/nginx/sites-available/booking.dhakulchan.net /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl enable nginx
sudo systemctl restart nginx

echo -e "\n${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}🔒 Step 11: Setup SSL Certificate (Let's Encrypt)${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}⚠️  Make sure DNS is pointing to this server first!${NC}"
echo -e "${YELLOW}⚠️  Run this command manually after DNS is configured:${NC}"
echo -e "${CYAN}sudo certbot --nginx -d booking.dhakulchan.net${NC}"

echo -e "\n${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}🔥 Step 12: Setup Firewall${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw --force enable

echo -e "\n${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}⏰ Step 13: Configure Timezone${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
sudo timedatectl set-timezone Asia/Bangkok

echo -e "\n${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║         Server Setup Completed Successfully!               ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${CYAN}📋 Next Steps:${NC}"
echo -e "1. Update DNS: Point booking.dhakulchan.net to 52.76.162.188"
echo -e "2. Setup SSL: ${CYAN}sudo certbot --nginx -d booking.dhakulchan.net${NC}"
echo -e "3. Update .env with production secrets"
echo -e "4. Restart services: ${CYAN}sudo systemctl restart booking-system nginx${NC}"
echo -e "5. Test: ${CYAN}https://booking.dhakulchan.net${NC}"
echo ""

echo -e "${CYAN}🛠️  Useful Commands:${NC}"
echo -e "Service status: ${CYAN}sudo systemctl status booking-system nginx mariadb${NC}"
echo -e "View logs: ${CYAN}sudo journalctl -u booking-system -f${NC}"
echo -e "Restart app: ${CYAN}sudo systemctl restart booking-system${NC}"
echo -e "Deploy updates: ${CYAN}./deploy_lightsail.sh${NC}"
echo ""
