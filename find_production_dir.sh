#!/bin/bash

echo "🔍 Finding voucher system directory..."

# Check common locations
POSSIBLE_DIRS=(
    "~/voucher-ro_v1.0"
    "~/voucher-system"
    "~/voucher-system1"
    "~/app"
    "~/application"
    "/var/www/voucher-ro_v1.0"
    "/var/www/voucher-system"
    "/var/www/html/voucher-ro_v1.0"
    "/opt/voucher-ro_v1.0"
    "/home/ubuntu/voucher-ro_v1.0"
    "/home/voucher/voucher-ro_v1.0"
)

echo "Searching in these locations:"
for dir in "${POSSIBLE_DIRS[@]}"; do
    expanded_dir=$(eval echo "$dir")
    echo "Checking: $expanded_dir"
    if [ -d "$expanded_dir" ]; then
        echo "✅ FOUND: $expanded_dir"
        if [ -f "$expanded_dir/app.py" ]; then
            echo "✅ CONFIRMED: Contains app.py - This is the voucher system!"
            echo ""
            echo "🎯 USE THIS DIRECTORY: $expanded_dir"
            echo ""
            echo "Commands to run:"
            echo "cd '$expanded_dir'"
            echo "ls -la"
            exit 0
        fi
    else
        echo "❌ Not found: $expanded_dir"
    fi
done

echo ""
echo "🔍 Let's search for any directory containing 'app.py' and 'voucher':"
find / -name "app.py" -type f 2>/dev/null | grep -i voucher | head -5

echo ""
echo "🔍 Let's search for directories containing 'voucher':"
find / -type d -name "*voucher*" 2>/dev/null | head -10

echo ""
echo "🔍 Let's check what's in home directory:"
ls -la ~/

echo ""
echo "🔍 Let's check common web directories:"
ls -la /var/www/ 2>/dev/null || echo "/var/www/ not found"
ls -la /opt/ 2>/dev/null || echo "/opt/ not found"