// Enhanced copyLineMessage Function with Line-specific features
window.copyLineMessage = async function (bookingId) {
    try {
        // Get button element and show loading state
        const button = event ? event.target : document.querySelector(`[onclick*="copyLineMessage('${bookingId}')"]`);
        const originalText = button ? button.textContent : 'Copy Line Message';

        if (button) {
            button.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>สร้างข้อความ Line...';
            button.disabled = true;
        }

        // Show loading toast
        showToast('🔄 กำลังสร้างข้อความ Line...', 'info');

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

            // Create Line-optimized message format
            const lineMessage = `สวัสดีครับ 
ต้องการสอบถามเรื่องการจอง ${bookingRef}

📋 Service Proposal: ${secureUrl}
🖼️ Download PNG: ${secureUrl}/png
📄 Download PDF: ${secureUrl}/pdf

📞 Tel: +662 2744216
📧 Email: support@dhakulchan.com
📱 Line OA: @dhakulchan

🔒 ลิงก์ปลอดภัย (หมดอายุใน ${expiryDays} วัน)`;

            // Show Line sharing options dialog
            showLineShareDialog(lineMessage, secureUrl, bookingRef);

        } else {
            throw new Error(data.message || 'ไม่สามารถสร้างข้อความ Line ได้');
        }

    } catch (error) {
        console.error('Copy Line Message error:', error);
        showToast(`❌ เกิดข้อผิดพลาด: ${error.message}`, 'error');
    } finally {
        // Restore button state
        if (button) {
            button.innerHTML = originalText;
            button.disabled = false;
        }
    }
};

// Line-specific sharing dialog
function showLineShareDialog(message, shareUrl, bookingRef) {
    // First copy to clipboard
    navigator.clipboard.writeText(message).then(() => {
        showToast('📋 ข้อความ Line ถูกคัดลอกแล้ว!', 'success');
    }).catch(() => {
        console.log('Clipboard copy failed');
    });

    const modalHtml = `
        <div class="modal fade" id="lineShareModal" tabindex="-1" aria-labelledby="lineShareModalLabel" aria-hidden="true">
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-header" style="background: linear-gradient(135deg, #00B900, #00C300); color: white;">
                        <h5 class="modal-title" id="lineShareModalLabel">
                            <i class="fab fa-line me-2"></i>
                            แชร์ผ่าน Line
                        </h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <div class="alert alert-success" role="alert">
                            <i class="fas fa-check-circle me-2"></i>
                            ข้อความได้ถูกคัดลอกไปยัง clipboard แล้ว
                        </div>
                        
                        <div class="row g-3">
                            <!-- Line App -->
                            <div class="col-12">
                                <button class="btn btn-success w-100 py-3" 
                                        onclick="openLineApp('${encodeURIComponent(message)}', '${shareUrl}')">
                                    <i class="fab fa-line fs-3 mb-2"></i><br>
                                    <strong>เปิดแอป Line</strong><br>
                                    <small>ส่งข้อความผ่านแอป Line บนมือถือ</small>
                                </button>
                            </div>
                            
                            <!-- Line Web -->
                            <div class="col-12">
                                <button class="btn btn-outline-success w-100 py-3" 
                                        onclick="openLineWeb('${encodeURIComponent(message)}', '${shareUrl}')">
                                    <i class="fas fa-globe fs-3 mb-2"></i><br>
                                    <strong>Line Web</strong><br>
                                    <small>เปิด Line ในเบราว์เซอร์</small>
                                </button>
                            </div>
                            
                            <!-- Line Official Account -->
                            <div class="col-12">
                                <button class="btn btn-info w-100 py-3" 
                                        onclick="openLineOA('@dhakulchan', '${encodeURIComponent(message)}')">
                                    <i class="fas fa-at fs-3 mb-2"></i><br>
                                    <strong>Line Official Account</strong><br>
                                    <small>ส่งข้อความไปยัง @dhakulchan</small>
                                </button>
                            </div>
                        </div>
                        
                        <hr class="my-3">
                        
                        <div class="row g-2">
                            <div class="col-6">
                                <button class="btn btn-outline-primary w-100" 
                                        onclick="copyLineMessage('${message.replace(/'/g, "\\'")}')">
                                    <i class="fas fa-copy me-2"></i>Copy อีกครั้ง
                                </button>
                            </div>
                            <div class="col-6">
                                <button class="btn btn-outline-secondary w-100" 
                                        onclick="previewLineMessage('${message.replace(/'/g, "\\'")}')">
                                    <i class="fas fa-eye me-2"></i>ดูตัวอย่าง
                                </button>
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <small class="text-muted w-100 text-center">
                            <i class="fab fa-line me-1 text-success"></i>
                            เหมาะสำหรับการติดต่อลูกค้าผ่าน Line
                        </small>
                    </div>
                </div>
            </div>
        </div>
    `;

    // Remove existing modal if any
    const existingModal = document.getElementById('lineShareModal');
    if (existingModal) {
        existingModal.remove();
    }

    // Add modal to page
    document.body.insertAdjacentHTML('beforeend', modalHtml);

    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('lineShareModal'));
    modal.show();

    // Clean up when modal is hidden
    document.getElementById('lineShareModal').addEventListener('hidden.bs.modal', function () {
        this.remove();
    });
}

// Line-specific functions
function openLineApp(encodedMessage, shareUrl) {
    const message = decodeURIComponent(encodedMessage);

    // Line app deep link
    const lineAppUrl = `line://msg/text/${encodedMessage}`;
    const lineWebUrl = `https://social-plugins.line.me/lineit/share?text=${encodedMessage}`;

    // Try Line app first, fallback to web
    window.location.href = lineAppUrl;

    // Fallback to web version after a short delay
    setTimeout(() => {
        window.open(lineWebUrl, '_blank');
    }, 1000);

    closeLineModal();
    showToast('📱 กำลังเปิดแอป Line...', 'info');
}

function openLineWeb(encodedMessage, shareUrl) {
    const lineWebUrl = `https://social-plugins.line.me/lineit/share?text=${encodedMessage}`;
    window.open(lineWebUrl, '_blank');

    closeLineModal();
    showToast('🌐 เปิด Line Web แล้ว', 'info');
}

function openLineOA(lineId, encodedMessage) {
    const message = decodeURIComponent(encodedMessage);

    // Line Official Account URL
    const lineOAUrl = `https://line.me/R/ti/p/${lineId}?text=${encodedMessage}`;
    window.open(lineOAUrl, '_blank');

    closeLineModal();
    showToast(`📞 เปิด Line OA ${lineId} แล้ว`, 'info');
}

function copyLineMessage(message) {
    navigator.clipboard.writeText(message).then(() => {
        showToast('📋 คัดลอกข้อความ Line เรียบร้อยแล้ว!', 'success');
    }).catch(() => {
        // Fallback
        const textArea = document.createElement('textarea');
        textArea.value = message;
        document.body.appendChild(textArea);
        textArea.select();

        try {
            document.execCommand('copy');
            showToast('📋 คัดลอกข้อความ Line เรียบร้อยแล้ว!', 'success');
        } catch (err) {
            showToast('❌ ไม่สามารถคัดลอกได้', 'error');
        }

        document.body.removeChild(textArea);
    });
}

function previewLineMessage(message) {
    const previewModalHtml = `
        <div class="modal fade" id="linePreviewModal" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header bg-success text-white">
                        <h5 class="modal-title">
                            <i class="fab fa-line me-2"></i>ตัวอย่างข้อความ Line
                        </h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="card">
                            <div class="card-header bg-light">
                                <small class="text-muted">ข้อความที่จะส่งใน Line:</small>
                            </div>
                            <div class="card-body">
                                <pre class="mb-0" style="white-space: pre-wrap; font-family: inherit;">${message}</pre>
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-success" onclick="copyLineMessage('${message.replace(/'/g, "\\'")}')">
                            <i class="fas fa-copy me-2"></i>คัดลอก
                        </button>
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">ปิด</button>
                    </div>
                </div>
            </div>
        </div>
    `;

    document.body.insertAdjacentHTML('beforeend', previewModalHtml);
    const previewModal = new bootstrap.Modal(document.getElementById('linePreviewModal'));
    previewModal.show();

    document.getElementById('linePreviewModal').addEventListener('hidden.bs.modal', function () {
        this.remove();
    });
}

function closeLineModal() {
    const modal = bootstrap.Modal.getInstance(document.getElementById('lineShareModal'));
    if (modal) {
        modal.hide();
    }
}
