#!/bin/bash

echo "🚨 Emergency Arial Font Deployment Starting..."

# Variables
PROJECT_DIR="~/voucher-ro_v1.0"
BACKUP_DIR="~/backup_$(date +%Y%m%d_%H%M%S)"
LOG_FILE="~/deployment_$(date +%Y%m%d_%H%M%S).log"

# Function to log messages
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Start deployment
log_message "🚀 Starting Emergency Arial Font Deployment"

# Navigate to project directory
cd "$PROJECT_DIR" || {
    log_message "❌ Failed to navigate to project directory"
    exit 1
}

# Create backup
log_message "📦 Creating backup..."
cp -r templates/ "$BACKUP_DIR/templates_backup/" 2>/dev/null

# Pull latest changes
log_message "🔄 Pulling latest changes from git..."
git fetch --all
git reset --hard origin/main

# Check if Arial template exists
if [ -f "templates/pdf/quote_template_arial_force.html" ]; then
    log_message "✅ Arial template found, copying..."
    cp templates/pdf/quote_template_arial_force.html templates/pdf/quote_template_final_v2.html
else
    log_message "❌ Arial template not found!"
    exit 1
fi

# Restart services
log_message "♻️ Restarting services..."
sudo systemctl restart voucher-system
sudo systemctl reload nginx

# Clear Python cache
log_message "🧹 Clearing Python cache..."
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Verify template
if [ -f "templates/pdf/quote_template_final_v2.html" ]; then
    ARIAL_COUNT=$(grep -c "Arial" templates/pdf/quote_template_final_v2.html)
    log_message "✅ Template updated successfully. Arial occurrences: $ARIAL_COUNT"
else
    log_message "❌ Template verification failed!"
    exit 1
fi

log_message "🎉 Emergency Arial Font Deployment Complete!"
log_message "📝 Log saved to: $LOG_FILE"
log_message "💾 Backup saved to: $BACKUP_DIR"

echo ""
echo "==========================================="
echo "🧪 TEST THESE URLs IMMEDIATELY:"
echo "==========================================="
echo "- https://service.dhakulchan.net/pre_receipt/quote-pdf/1/pdf?cache_bust=v10"
echo "- https://service.dhakulchan.net/booking/1/quote-pdf?cache_bust=v10"
echo "- https://service.dhakulchan.net/voucher/1/quote-pdf?cache_bust=v10"
echo "==========================================="