#!/bin/bash

echo "🎯 CORRECT DIRECTORY FOUND: /opt/voucher-ro"
echo "🚀 Deploying Arial font fix..."

# Navigate to correct directory
cd /opt/voucher-ro || {
    echo "❌ Cannot access /opt/voucher-ro"
    exit 1
}

echo "📁 Current directory: $(pwd)"
echo "📂 Contents:"
ls -la

# Check if we have git repo
if [ -d ".git" ]; then
    echo "✅ Git repository found"
    
    # Pull latest changes
    echo "🔄 Pulling latest changes..."
    git fetch --all
    git reset --hard origin/main
    
    # Check if Arial template exists
    if [ -f "templates/pdf/quote_template_arial_force.html" ]; then
        echo "✅ Arial template found, copying..."
        cp templates/pdf/quote_template_arial_force.html templates/pdf/quote_template_final_v2.html
        echo "✅ Template copied successfully"
    else
        echo "❌ Arial template not found!"
        echo "Available templates:"
        ls -la templates/pdf/ | grep quote
        exit 1
    fi
else
    echo "❌ No git repository found"
    echo "We need to clone or update the repository"
fi

# Find correct service name
echo "🔍 Finding service name..."
SERVICES=$(systemctl list-units --type=service | grep -E "(voucher|gunicorn)" | awk '{print $1}')
echo "Found services: $SERVICES"

# Check common service names
for service in voucher-ro voucher gunicorn voucher.service; do
    if systemctl is-active --quiet "$service"; then
        echo "✅ Found active service: $service"
        echo "🔄 Restarting $service..."
        sudo systemctl restart "$service"
        break
    fi
done

# Restart nginx
echo "🔄 Restarting nginx..."
sudo systemctl reload nginx

# Clear Python cache
echo "🧹 Clearing Python cache..."
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

echo "🎉 Deployment completed!"
echo ""
echo "🧪 Test URLs:"
echo "- https://service.dhakulchan.net/pre_receipt/quote-pdf/1/pdf?cache_bust=v11"
echo "- https://service.dhakulchan.net/booking/1/quote-pdf?cache_bust=v11"