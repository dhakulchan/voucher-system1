#!/bin/bash

echo "🔒 SSL Auto Renewal Setup for service.dhakulchan.net"
echo "=================================================="

LIGHTSAIL_IP="54.255.136.172"
LIGHTSAIL_USER="bitnami"
SSH_KEY="~/.ssh/LightsailDefaultKey-ap-southeast-1.pem"
DOMAIN="service.dhakulchan.net"

# Function to print colored output
print_status() {
    echo -e "\033[0;32m✅ $1\033[0m"
}

print_info() {
    echo -e "\033[0;34mℹ️  $1\033[0m"
}

print_warning() {
    echo -e "\033[1;33m⚠️  $1\033[0m"
}

# Test SSH connection
print_info "Testing SSH connection to Lightsail instance..."
if ! ssh -i "$SSH_KEY" -o ConnectTimeout=10 "$LIGHTSAIL_USER@$LIGHTSAIL_IP" "echo 'SSH OK'" 2>/dev/null; then
    echo "❌ SSH connection failed"
    exit 1
fi

print_status "SSH connection successful"

# Execute SSL setup script on remote server
print_info "Setting up SSL auto renewal on server..."
ssh -i "$SSH_KEY" "$LIGHTSAIL_USER@$LIGHTSAIL_IP" << 'EOF'

echo "🔧 Setting up SSL auto renewal..."

# Create SSL renewal script
sudo tee /home/bitnami/ssl_renewal.sh > /dev/null << 'RENEWAL_SCRIPT'
#!/bin/bash

# SSL Certificate Auto Renewal Script
# Runs every 89 days to renew Let's Encrypt certificates

DOMAIN="service.dhakulchan.net"
LOG_FILE="/var/log/ssl_renewal.log"
EMAIL="admin@dhakulchan.net"

# Function to log with timestamp
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | sudo tee -a "$LOG_FILE"
}

# Function to send notification (optional)
send_notification() {
    local subject="$1"
    local message="$2"
    
    # Send email notification if mail is configured
    if command -v mail >/dev/null 2>&1; then
        echo "$message" | mail -s "$subject" "$EMAIL" 2>/dev/null || true
    fi
    
    # Log to syslog
    logger -t ssl_renewal "$subject: $message"
}

log_message "Starting SSL certificate renewal process"

# Check current certificate expiry
CERT_FILE="/opt/bitnami/apache/conf/bitnami/certs/server.crt"
if [ -f "$CERT_FILE" ]; then
    EXPIRY_DATE=$(openssl x509 -enddate -noout -in "$CERT_FILE" | cut -d= -f2)
    EXPIRY_EPOCH=$(date -d "$EXPIRY_DATE" +%s)
    CURRENT_EPOCH=$(date +%s)
    DAYS_UNTIL_EXPIRY=$(( (EXPIRY_EPOCH - CURRENT_EPOCH) / 86400 ))
    
    log_message "Current certificate expires in $DAYS_UNTIL_EXPIRY days ($EXPIRY_DATE)"
    
    # Only renew if certificate expires in less than 30 days
    if [ $DAYS_UNTIL_EXPIRY -gt 30 ]; then
        log_message "Certificate is still valid for $DAYS_UNTIL_EXPIRY days. No renewal needed."
        exit 0
    fi
else
    log_message "Certificate file not found. Proceeding with renewal."
fi

# Stop Apache before renewal
log_message "Stopping Apache for certificate renewal"
sudo /opt/bitnami/ctlscript.sh stop apache

# Run bncert-tool for automatic renewal
log_message "Running bncert-tool for certificate renewal"

# Create bncert configuration file
sudo tee /tmp/bncert_config.txt > /dev/null << BNCERT_CONFIG
$DOMAIN
Y
Y
admin@dhakulchan.net
Y
BNCERT_CONFIG

# Run bncert-tool with configuration
if sudo /opt/bitnami/bncert-tool < /tmp/bncert_config.txt >> "$LOG_FILE" 2>&1; then
    log_message "SSL certificate renewed successfully"
    send_notification "SSL Renewal Success" "SSL certificate for $DOMAIN has been renewed successfully"
    
    # Verify new certificate
    if [ -f "$CERT_FILE" ]; then
        NEW_EXPIRY_DATE=$(openssl x509 -enddate -noout -in "$CERT_FILE" | cut -d= -f2)
        log_message "New certificate expires on: $NEW_EXPIRY_DATE"
    fi
    
    # Test Apache configuration
    if sudo /opt/bitnami/apache/bin/httpd -t; then
        log_message "Apache configuration test passed"
    else
        log_message "WARNING: Apache configuration test failed"
        send_notification "SSL Renewal Warning" "SSL certificate renewed but Apache configuration test failed"
    fi
    
else
    log_message "ERROR: SSL certificate renewal failed"
    send_notification "SSL Renewal Failed" "SSL certificate renewal for $DOMAIN failed. Please check manually."
fi

# Start Apache
log_message "Starting Apache"
sudo /opt/bitnami/ctlscript.sh start apache

# Test website accessibility
log_message "Testing website accessibility"
if curl -s -f "https://$DOMAIN" > /dev/null; then
    log_message "Website is accessible via HTTPS"
    send_notification "SSL Renewal Complete" "SSL certificate renewal completed and website is accessible"
else
    log_message "WARNING: Website is not accessible via HTTPS"
    send_notification "SSL Renewal Issue" "SSL certificate renewal completed but website is not accessible"
fi

# Cleanup
sudo rm -f /tmp/bncert_config.txt

log_message "SSL renewal process completed"
RENEWAL_SCRIPT

# Make script executable
sudo chmod +x /home/bitnami/ssl_renewal.sh

# Create log file
sudo touch /var/log/ssl_renewal.log
sudo chown bitnami:bitnami /var/log/ssl_renewal.log

echo "✅ SSL renewal script created"

# Setup cron job for// Enhanced sharePublic Function with Multi-Platform Support
window.sharePublic = async function (bookingId) {
    try {
        // Get button element and show loading state
        const button = event ? event.target : document.querySelector(`[onclick*="sharePublic('${bookingId}')"]`);
        const originalText = button ? button.textContent : 'Share Public Message';

        if (button) {
            button.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>สร้างลิงก์แชร์...';
            button.disabled = true;
        }

        // Show loading toast
        showToast('🔄 กำลังสร้างลิงก์แชร์ที่ปลอดภัย...', 'info');

        // Get secure token-based URL (30-day expiration)
        const response = await fetch(`/api/share/booking/${bookingId}/url`);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();

        if (data.success) {
            const secureUrl = data.secure_url || data.share_url;
            const bookingRef = data.booking_reference;
            const expiryDays = data.expires_in_days || 30;

            // Create comprehensive share message
            const shareMessage = `📋 Service Proposal - Booking ${bookingRef}

🔗 View Details: ${secureUrl}
🖼️ Download PNG: ${secureUrl}/png  
📄 Download PDF: ${secureUrl}/pdf

📞 Contact us:
Tel: +662 2744216
Email: support@dhakulchan.com
Line OA: @dhakulchan

🔒 Secure link (expires in ${expiryDays} days)`;

            // Detect platform and use appropriate sharing method
            const isMobile = /Android|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);

            // Try native sharing first on mobile
            if (navigator.share && isMobile) {
                try {
                    await navigator.share({
                        title: `Service Proposal - ${bookingRef}`,
                        text: shareMessage,
                        url: secureUrl
                    });
                    showToast('📤 แชร์ Service Proposal เรียบร้อยแล้ว!', 'success');
                    return;
                } catch (shareError) {
                    // User cancelled or share failed, fall back to custom dialog
                    console.log('Native share cancelled or failed:', shareError);
                }
            }

            // Show enhanced platform selection dialog
            showMultiPlatformShareDialog(shareMessage, secureUrl, bookingRef);

        } else {
            throw new Error(data.message || 'ไม่สามารถสร้างลิงก์แชร์ได้');
        }

    } catch (error) {
        console.error('Share error:', error);
        showToast(`❌ เกิดข้อผิดพลาด: ${error.message}`, 'error');
    } finally {
        // Restore button state
        if (button) {
            button.innerHTML = originalText;
            button.disabled = false;
        }
    }
};

// Enhanced Multi-Platform Share Dialog
function showMultiPlatformShareDialog(message, shareUrl, bookingRef) {
    // First copy to clipboard
    navigator.clipboard.writeText(message).then(() => {
        showToast('📋 ข้อความถูกคัดลอกไปยัง clipboard แล้ว!', 'success');
    }).catch(() => {
        console.log('Clipboard copy failed, will show fallback');
    });

    // Create modal dialog with platform options
    const modalHtml = `
        <div class="modal fade" id="shareModal" tabindex="-1" aria-labelledby="shareModalLabel" aria-hidden="true">
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-header bg-primary text-white">
                        <h5 class="modal-title" id="shareModalLabel">
                            <i class="fas fa-share-alt me-2"></i>
                            เลือกแพลตฟอร์มที่ต้องการแชร์
                        </h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <p class="text-muted mb-3">
                            <i class="fas fa-check-circle text-success me-2"></i>
                            ข้อความได้ถูกคัดลอกไปยัง clipboard แล้ว
                        </p>
                        
                        <div class="row g-2">
                            <!-- WhatsApp -->
                            <div class="col-6">
                                <button class="btn btn-success w-100 share-platform-btn" 
                                        onclick="openPlatform('whatsapp', '${encodeURIComponent(message)}', '${shareUrl}')">
                                    <i class="fab fa-whatsapp fs-4 mb-1"></i><br>
                                    <small>WhatsApp</small>
                                </button>
                            </div>
                            
                            <!-- Line -->
                            <div class="col-6">
                                <button class="btn btn-success w-100 share-platform-btn" 
                                        onclick="openPlatform('line', '${encodeURIComponent(message)}', '${shareUrl}')">
                                    <i class="fab fa-line fs-4 mb-1"></i><br>
                                    <small>Line</small>
                                </button>
                            </div>
                            
                            <!-- Facebook -->
                            <div class="col-6">
                                <button class="btn btn-primary w-100 share-platform-btn" 
                                        onclick="openPlatform('facebook', '${encodeURIComponent(message)}', '${shareUrl}')">
                                    <i class="fab fa-facebook fs-4 mb-1"></i><br>
                                    <small>Facebook</small>
                                </button>
                            </div>
                            
                            <!-- Email -->
                            <div class="col-6">
                                <button class="btn btn-info w-100 share-platform-btn" 
                                        onclick="openPlatform('email', '${encodeURIComponent(message)}', '${shareUrl}', '${bookingRef}')">
                                    <i class="fas fa-envelope fs-4 mb-1"></i><br>
                                    <small>Email</small>
                                </button>
                            </div>
                            
                            <!-- Telegram -->
                            <div class="col-6">
                                <button class="btn btn-info w-100 share-platform-btn" 
                                        onclick="openPlatform('telegram', '${encodeURIComponent(message)}', '${shareUrl}')">
                                    <i class="fab fa-telegram fs-4 mb-1"></i><br>
                                    <small>Telegram</small>
                                </button>
                            </div>
                            
                            <!-- Twitter -->
                            <div class="col-6">
                                <button class="btn btn-dark w-100 share-platform-btn" 
                                        onclick="openPlatform('twitter', '${encodeURIComponent(message)}', '${shareUrl}')">
                                    <i class="fab fa-twitter fs-4 mb-1"></i><br>
                                    <small>Twitter</small>
                                </button>
                            </div>
                        </div>
                        
                        <hr class="my-3">
                        
                        <!-- Direct Actions -->
                        <div class="row g-2">
                            <div class="col-6">
                                <button class="btn btn-outline-primary w-100" 
                                        onclick="copyToClipboard('${message.replace(/'/g, "\\'")}')">
                                    <i class="fas fa-copy me-2"></i>Copy Message
                                </button>
                            </div>
                            <div class="col-6">
                                <button class="btn btn-outline-secondary w-100" 
                                        onclick="openSharePage('${shareUrl}')">
                                    <i class="fas fa-external-link-alt me-2"></i>Open Page
                                </button>
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <small class="text-muted w-100 text-center">
                            <i class="fas fa-shield-alt me-1"></i>
                            ลิงก์ปลอดภัย หมดอายุใน 30 วัน
                        </small>
                    </div>
                </div>
            </div>
        </div>
    `;

    // Remove existing modal if any
    const existingModal = document.getElementById('shareModal');
    if (existingModal) {
        existingModal.remove();
    }

    // Add modal to page
    document.body.insertAdjacentHTML('beforeend', modalHtml);

    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('shareModal'));
    modal.show();

    // Clean up when modal is hidden
    document.getElementById('shareModal').addEventListener('hidden.bs.modal', function () {
        this.remove();
    });
}

// Platform-specific sharing functions
function openPlatform(platform, encodedMessage, shareUrl, bookingRef) {
    let url;
    const message = decodeURIComponent(encodedMessage);

    switch (platform) {
        case 'whatsapp':
            url = `https://wa.me/?text=${encodedMessage}`;
            break;

        case 'line':
            // Line sharing with text
            url = `https://social-plugins.line.me/lineit/share?url=${encodeURIComponent(shareUrl)}&text=${encodedMessage}`;
            break;

        case 'facebook':
            url = `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(shareUrl)}&quote=${encodedMessage}`;
            break;

        case 'twitter':
            url = `https://twitter.com/intent/tweet?text=${encodedMessage}`;
            break;

        case 'telegram':
            url = `https://t.me/share/url?url=${encodeURIComponent(shareUrl)}&text=${encodedMessage}`;
            break;

        case 'email':
            const subject = `Service Proposal - Booking ${bookingRef}`;
            url = `mailto:?subject=${encodeURIComponent(subject)}&body=${encodedMessage}`;
            break;

        default:
            url = shareUrl;
    }

    // Open in new window/tab
    window.open(url, '_blank', 'width=600,height=400');

    // Close modal
    const modal = bootstrap.Modal.getInstance(document.getElementById('shareModal'));
    if (modal) {
        modal.hide();
    }

    showToast(`📱 เปิด ${platform.charAt(0).toUpperCase() + platform.slice(1)} แล้ว`, 'info');
}

// Helper functions
function copyToClipboard(message) {
    navigator.clipboard.writeText(message).then(() => {
        showToast('📋 คัดลอกข้อความเรียบร้อยแล้ว!', 'success');
    }).catch(() => {
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = message;
        document.body.appendChild(textArea);
        textArea.select();

        try {
            document.execCommand('copy');
            showToast('📋 คัดลอกข้อความเรียบร้อยแล้ว!', 'success');
        } catch (err) {
            showToast('❌ ไม่สามารถคัดลอกได้', 'error');
        }

        document.body.removeChild(textArea);
    });

    // Close modal
    const modal = bootstrap.Modal.getInstance(document.getElementById('shareModal'));
    if (modal) {
        modal.hide();
    }
}

function openSharePage(shareUrl) {
    window.open(shareUrl, '_blank');

    // Close modal
    const modal = bootstrap.Modal.getInstance(document.getElementById('shareModal'));
    if (modal) {
        modal.hide();
    }

    showToast('🌐 เปิดหน้าแชร์แล้ว', 'info');
}

// Add CSS for share buttons
const shareModalStyles = `
<style>
.share-platform-btn {
    aspect-ratio: 1;
    border-radius: 10px;
    transition: all 0.3s ease;
    font-size: 0.85rem;
}

.share-platform-btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

.share-platform-btn i {
    transition: all 0.3s ease;
}

.share-platform-btn:hover i {
    transform: scale(1.1);
}

#shareModal .modal-content {
    border-radius: 15px;
    border: none;
    box-shadow: 0 10px 40px rgba(0,0,0,0.1);
}

#shareModal .modal-header {
    border-top-left-radius: 15px;
    border-top-right-radius: 15px;
    border-bottom: none;
}

#shareModal .modal-footer {
    border-top: 1px solid #dee2e6;
    border-bottom-left-radius: 15px;
    border-bottom-right-radius: 15px;
}
</style>
`;

// Add styles to head if not already added
if (!document.querySelector('#shareModalStyles')) {
    const styleElement = document.createElement('div');
    styleElement.id = 'shareModalStyles';
    styleElement.innerHTML = shareModalStyles;
    document.head.appendChild(styleElement);
}
