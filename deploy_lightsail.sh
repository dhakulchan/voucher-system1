#!/bin/bash
#═══════════════════════════════════════════════════════════════════════════
# AWS Lightsail Deployment Script
# Instance: booking-dhakulchan-prod
# Domain: https://booking.dhakulchan.net
# Region: Singapore (ap-southeast-1a)
#═══════════════════════════════════════════════════════════════════════════

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SERVER_IP="52.76.162.188"
SERVER_USER="admin"
SSH_KEY="${HOME}/voucher-ro_v1.1/.ssh/LightsailDefaultKey-ap-southeast-1.pem"
DOMAIN="booking.dhakulchan.net"
APP_DIR="/var/www/booking"
SERVICE_NAME="booking-system"
GITHUB_REPO="https://github.com/dhakulchan/voucher-system1.git"

echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║     AWS Lightsail Deployment - Booking System             ║${NC}"
echo -e "${CYAN}║     Domain: ${DOMAIN}                      ║${NC}"
echo -e "${CYAN}║     IP: ${SERVER_IP}                              ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Function to print status
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Check if SSH key exists
if [ ! -f "$SSH_KEY" ]; then
    print_error "SSH key not found: $SSH_KEY"
    print_info "Please download the key from AWS Lightsail Console"
    print_info "Path should be: ${SSH_KEY}"
    exit 1
fi

print_status "SSH key found"

# Set correct permissions for SSH key
chmod 400 "$SSH_KEY"

# Test SSH connection
print_info "Testing SSH connection to $SERVER_IP..."
if ssh -i "$SSH_KEY" -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$SERVER_USER@$SERVER_IP" "echo 'SSH OK'" 2>/dev/null; then
    print_status "SSH connection successful"
else
    print_error "SSH connection failed"
    print_info "Make sure the instance is running and the IP is correct"
    exit 1
fi

# Deploy to server
print_info "Starting deployment to AWS Lightsail..."

ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$SERVER_USER@$SERVER_IP" << 'ENDSSH'
set -e

echo "═══════════════════════════════════════════════════════════════════"
echo "📦 Pulling latest changes from GitHub..."
echo "═══════════════════════════════════════════════════════════════════"
cd /var/www/booking
git fetch --all
git reset --hard origin/main
git pull origin main

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "🐍 Activating virtual environment..."
echo "═══════════════════════════════════════════════════════════════════"
source venv/bin/activate

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "📚 Installing/Updating Python dependencies..."
echo "═══════════════════════════════════════════════════════════════════"
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "🗃️ Checking database status..."
echo "═══════════════════════════════════════════════════════════════════"
sudo systemctl status mariadb --no-pager -l || echo "MariaDB status check done"

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "🔄 Restarting services..."
echo "═══════════════════════════════════════════════════════════════════"
sudo systemctl restart booking-system
sleep 3
sudo systemctl reload nginx

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "🧹 Cleaning up..."
echo "═══════════════════════════════════════════════════════════════════"
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "✅ Deployment completed successfully!"
echo "═══════════════════════════════════════════════════════════════════"

ENDSSH

print_status "Deployment completed"

# Check service status
print_info "Checking service status..."
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$SERVER_USER@$SERVER_IP" "sudo systemctl is-active booking-system nginx mariadb" || print_warning "Some services may need attention"

print_status "Service status check completed"

# Test URL
print_info "Testing application..."
sleep 5
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -k "https://$DOMAIN" || echo "000")

if [ "$HTTP_CODE" -eq 200 ] || [ "$HTTP_CODE" -eq 302 ]; then
    print_status "Application is responding (HTTP $HTTP_CODE)"
elif [ "$HTTP_CODE" -eq 000 ]; then
    print_warning "Could not connect to application. DNS may not be configured yet."
    print_info "You can test directly: curl -I http://$SERVER_IP"
else
    print_warning "Application returned HTTP $HTTP_CODE"
fi

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║           Deployment Completed Successfully!              ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}🌐 Application URL: https://$DOMAIN${NC}"
echo -e "${BLUE}📅 Calendar: https://$DOMAIN/booking/calendar${NC}"
echo -e "${BLUE}🔐 Login: https://$DOMAIN/login${NC}"
echo -e "${BLUE}📊 Direct IP: http://$SERVER_IP${NC}"
echo ""
echo -e "${CYAN}📝 View logs: ssh -i $SSH_KEY $SERVER_USER@$SERVER_IP 'sudo journalctl -u booking-system -f'${NC}"
echo ""
