#!/bin/bash

# Arial Font Emergency Deployment Script
# Run this on production server at /opt/voucher-ro

set -e  # Exit on any error

echo "🚨 EMERGENCY ARIAL FONT DEPLOYMENT STARTING..."
echo "📅 $(date)"

# Check if we're in the right directory
if [[ ! -f "app.py" ]]; then
    echo "❌ app.py not found. Are we in the right directory?"
    echo "Current directory: $(pwd)"
    echo "Trying to navigate to /opt/voucher-ro..."
    cd /opt/voucher-ro || {
        echo "❌ Cannot access /opt/voucher-ro"
        exit 1
    }
fi

echo "✅ Working directory: $(pwd)"

# Step 1: Backup current template
echo "📦 Creating backup..."
if [[ -f "templates/pdf/quote_template_final_v2.html" ]]; then
    cp templates/pdf/quote_template_final_v2.html templates/pdf/quote_template_final_v2.html.backup.$(date +%Y%m%d_%H%M%S)
    echo "✅ Backup created"
fi

# Step 2: Pull latest changes
echo "🔄 Updating from git..."
if [[ -d ".git" ]]; then
    git fetch --all
    git reset --hard origin/main
    echo "✅ Git updated"
else
    echo "⚠️ No git repository found. Manual template update needed."
fi

# Step 3: Copy Arial template
if [[ -f "templates/pdf/quote_template_arial_force.html" ]]; then
    echo "📄 Copying Arial template..."
    cp templates/pdf/quote_template_arial_force.html templates/pdf/quote_template_final_v2.html
    
    # Verify Arial font is applied
    ARIAL_COUNT=$(grep -c "Arial" templates/pdf/quote_template_final_v2.html || echo "0")
    echo "✅ Arial template copied. Font occurrences: $ARIAL_COUNT"
else
    echo "❌ Arial template not found in templates/pdf/"
    echo "Available templates:"
    ls -la templates/pdf/ | grep -E "\.(html|htm)$" || echo "No templates found"
    exit 1
fi

# Step 4: Find and restart services
echo "🔍 Finding running services..."

# Find gunicorn processes
GUNICORN_PIDS=$(ps aux | grep "[g]unicorn.*voucher-ro" | awk '{print $2}' || echo "")
if [[ -n "$GUNICORN_PIDS" ]]; then
    echo "🔄 Stopping gunicorn processes: $GUNICORN_PIDS"
    sudo kill -TERM $GUNICORN_PIDS 2>/dev/null || echo "⚠️ Some processes already stopped"
    sleep 2
    
    # Force kill if still running
    STILL_RUNNING=$(ps aux | grep "[g]unicorn.*voucher-ro" | awk '{print $2}' || echo "")
    if [[ -n "$STILL_RUNNING" ]]; then
        sudo kill -KILL $STILL_RUNNING 2>/dev/null || echo "⚠️ Force kill completed"
    fi
fi

# Check common systemd services
for service in gunicorn voucher-ro voucher; do
    if systemctl is-enabled "$service" >/dev/null 2>&1; then
        echo "🔄 Restarting systemd service: $service"
        sudo systemctl restart "$service"
    fi
done

# Step 5: Restart nginx
echo "🔄 Restarting nginx..."
sudo systemctl reload nginx

# Step 6: Clear Python cache
echo "🧹 Clearing Python cache..."
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Step 7: Verify deployment
echo "✅ Checking if services are running..."
sleep 3

# Check if new gunicorn processes started
NEW_PROCESSES=$(ps aux | grep "[g]unicorn.*voucher-ro" | wc -l)
echo "📊 Gunicorn processes running: $NEW_PROCESSES"

# Check if template exists and has Arial
if [[ -f "templates/pdf/quote_template_final_v2.html" ]]; then
    ARIAL_FINAL=$(grep -c "Arial" templates/pdf/quote_template_final_v2.html || echo "0")
    echo "📄 Final template Arial count: $ARIAL_FINAL"
else
    echo "❌ Final template not found!"
fi

echo ""
echo "🎉 DEPLOYMENT COMPLETED!"
echo "📅 $(date)"
echo ""
echo "🧪 TEST THESE URLs IMMEDIATELY:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "https://service.dhakulchan.net/pre_receipt/quote-pdf/1/pdf?cache_bust=v12"
echo "https://service.dhakulchan.net/booking/1/quote-pdf?cache_bust=v12"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🔍 If fonts still don't show, check browser cache:"
echo "- Hard refresh (Ctrl+F5 or Cmd+Shift+R)"
echo "- Clear browser cache"
echo "- Try incognito/private mode"