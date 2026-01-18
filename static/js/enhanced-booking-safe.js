/**
 * 🛡️ Enhanced Booking JavaScript - Extracted from Template
 * REASON: Prevent Jinja2/JavaScript syntax corruption in view_en.html
 * DATE: 2025-10-14 (After corruption #7)
 */

// Global booking data - will be populated by template
window.currentBookingData = null;

/**
 * Get current booking ID safely
 * @returns {number|null} Booking ID or null if not available
 */
function getCurrentBookingId() {
    const bookingData = document.getElementById('booking-data');
    if (bookingData && bookingData.dataset.bookingId) {
        return parseInt(bookingData.dataset.bookingId);
    }

    // Fallback to global data
    if (window.currentBookingData && window.currentBookingData.id) {
        return window.currentBookingData.id;
    }

    console.warn('Booking ID not found');
    return null;
}

/**
 * Initialize booking data from DOM
 */
function initializeBookingData() {
    const bookingDataElement = document.getElementById('booking-data');
    if (bookingDataElement) {
        window.currentBookingData = {
            id: parseInt(bookingDataElement.dataset.bookingId) || null,
            reference: bookingDataElement.dataset.bookingReference || '',
            status: bookingDataElement.dataset.bookingStatus || '',
            quoteNumber: bookingDataElement.dataset.quoteNumber || null
        };

        console.log('Booking data initialized:', window.currentBookingData);
    }
}

/**
 * Enhanced toast notification with better styling
 * @param {string} message Toast message
 * @param {string} type Toast type: 'success', 'error', 'info', 'warning'
 */
function showToast(message, type = 'info') {
    const toastClass = {
        'success': 'bg-success',
        'error': 'bg-danger',
        'info': 'bg-info',
        'warning': 'bg-warning'
    };

    const bgClass = toastClass[type] || 'bg-info';

    // Remove existing toasts
    const existingToasts = document.querySelectorAll('.toast-notification');
    existingToasts.forEach(toast => toast.remove());

    // Create toast element
    const toast = document.createElement('div');
    toast.className = `toast-notification position-fixed ${bgClass} text-white p-3 rounded shadow-lg`;
    toast.style.cssText = `
        top: 20px;
        right: 20px;
        z-index: 9999;
        min-width: 300px;
        animation: slideInRight 0.3s ease-out;
    `;

    // Toast content
    toast.innerHTML = `
        <div class="d-flex align-items-center">
            <div class="flex-grow-1">${message}</div>
            <button type="button" class="btn-close btn-close-white ms-2" onclick="this.parentElement.parentElement.remove()"></button>
        </div>
    `;

    // Add to document
    document.body.appendChild(toast);

    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (toast.parentElement) {
            toast.style.animation = 'slideOutRight 0.3s ease-in';
            setTimeout(() => toast.remove(), 300);
        }
    }, 5000);
}

/**
 * Share to LINE Official Account
 * @param {string} message Message to share
 */
function shareToLineOA(message) {
    const lineUrl = `https://line.me/R/msg/text/?${encodeURIComponent(message)}`;
    window.open(lineUrl, '_blank');
    showToast('📱 เปิด LINE เพื่อแชร์...', 'success');
}

/**
 * Share to Email
 * @param {string} subject Email subject
 * @param {string} body Email body
 */
function shareToEmail(subject, body) {
    const emailUrl = `mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
    window.location.href = emailUrl;
    showToast('📧 เปิดแอปอีเมล...', 'success');
}

/**
 * Share to Facebook
 * @param {string} message Message to share
 */
function shareToFacebook(message) {
    const facebookUrl = `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(window.location.href)}&quote=${encodeURIComponent(message)}`;
    window.open(facebookUrl, '_blank');
    showToast('📘 เปิด Facebook...', 'success');
}

/**
 * Share to Twitter
 * @param {string} message Message to share
 */
function shareToTwitter(message) {
    const twitterUrl = `https://twitter.com/intent/tweet?text=${encodeURIComponent(message)}&url=${encodeURIComponent(window.location.href)}`;
    window.open(twitterUrl, '_blank');
    showToast('🐦 เปิด Twitter...', 'success');
}

/**
 * Share to Telegram
 * @param {string} message Message to share
 */
function shareToTelegram(message) {
    const telegramUrl = `https://t.me/share/url?url=${encodeURIComponent(window.location.href)}&text=${encodeURIComponent(message)}`;
    window.open(telegramUrl, '_blank');
    showToast('✈️ เปิด Telegram...', 'success');
}

/**
 * Copy to clipboard
 * @param {string} text Text to copy
 */
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        showToast('📋 คัดลอกข้อความแล้ว!', 'success');
    } catch (err) {
        console.error('Failed to copy text:', err);
        showToast('❌ ไม่สามารถคัดลอกได้', 'error');
    }
}

/**
 * Generate enhanced message and secure URLs
 * @param {number} bookingId Booking ID
 * @returns {Promise<Object>} Object containing message and data
 */
async function generateEnhancedMessage(bookingId) {
    try {
        console.log('🔧 Generating enhanced message for booking:', bookingId);
        const response = await fetch(`/api/share/booking/${bookingId}/url`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include'  // Include cookies for authentication
        });

        console.log('📡 Generate message response:', response.status, response.statusText);

        if (!response.ok) {
            if (response.status === 401) {
                throw new Error('Please login to access this feature');
            } else if (response.status === 404) {
                throw new Error('Booking not found');
            } else {
                const errorText = await response.text();
                throw new Error(`Server error: ${response.status} - ${errorText}`);
            }
        }

        const data = await response.json();
        console.log('📝 Generated data:', data);

        if (data.success) {
            // สร้าง message ภาษาไทยตามสถานะ booking
            let message = '';
            const bookingData = window.currentBookingData;
            const bookingStatus = bookingData ? bookingData.status : 'pending';

            if (bookingStatus === 'completed') {
                message = `สวัสดีค่ะ
บริษัท ตระกูลเฉินฯ ขอขอบคุณที่ให้เราดูแลการเดินทางของท่าน หมายเลขอ้างอิง ${data.booking_reference}

🎫 Tour Voucher: ${data.secure_url}

🖼️ Download PNG: ${data.png_url || `${data.secure_url}/png`}

📄 Download PDF: ${data.pdf_url || `${data.secure_url}/pdf`}

Thank you for letting us take care of you. Have a safe journey, and we hope to see you again!
ขอบคุณที่ให้เราดูแลท่าน ขอให้เดินทางปลอดภัย และหวังว่าจะได้พบกันอีก!

ติดต่อสอบถามข้อมูลเพิ่มเติม:
📞 Tel: BKK +662 2744216  📞 Tel: HKG +852 23921155
📧 Email: booking@dhakulchan.com
📱 Line OA: @dhakulchan | @changuru
🏛️ รู้จักตระกูลเฉินฯ: https://www.dhakulchan.net/page/about-dhakulchan`;
            } else if (bookingStatus === 'vouchered') {
                message = `สวัสดีค่ะ
บริษัท ตระกูลเฉินฯ แจ้งส่ง Tour Voucher หมายเลขอ้างอิง ${data.booking_reference}
กรุณาคลิกดูรายละเอียดตามด้านล่างค่ะ

🎫 Tour Voucher: ${data.secure_url}

🖼️ Download PNG: ${data.png_url || `${data.secure_url}/png`}

📄 Download PDF: ${data.pdf_url || `${data.secure_url}/pdf`}

ติดต่อสอบถามข้อมูลเพิ่มเติม:
📞 Tel: BKK +662 2744216  📞 Tel: HKG +852 23921155
📧 Email: booking@dhakulchan.com
📱 Line OA: @dhakulchan | @changuru
🏛️ รู้จักตระกูลเฉินฯ: https://www.dhakulchan.net/page/about-dhakulchan`;
            } else {
                // Default message for other statuses
                message = `สวัสดีค่ะ
บริษัท ตระกูลเฉินฯ แจ้งรายละเอียดบริการหรือรายการทัวร์ หมายเลขอ้างอิง ${data.booking_reference}

กรุณาคลิกดูรายละเอียดตามด้านล่างค่ะ

📋 Service Proposal: ${data.secure_url}

━━━━━━━━━
💡แนะนำการใช้งาน
━━━━━━━━━

1) เปิดลิงก์
• เปิดได้ทั้งมือถือ/คอม ไม่ต้องล็อกอิน

2) ตรวจสอบข้อมูล
• ข้อมูลลูกค้า / วันเดินทาง / จำนวนคน
• รายชื่อผู้เดินทาง (ตรงพาสปอร์ต)
• ดาวน์โหลด: E-Ticket, Confirmation, Proposal, Quote, Voucher
• คลิกลิงก์: รายการทัวร์-คู่มือท่องเที่ยว 

3) ดาวน์โหลดเอกสาร
🔴 PNG = ใช้บนมือถือ/พิมพ์
🟣 PDF = เก็บในคอม/ส่งอีเมล
❌ ห้ามแชร์ลิงก์
⏰ หมดอายุ 120 วัน

ติดต่อสอบถามข้อมูลเพิ่มเติม:
📞 Tel: BKK +662 2744216  📞 Tel: HKG +852 23921155
📧 Email: booking@dhakulchan.com
📱 Line OA: @dhakulchan | @changuru
🏛️ รู้จักตระกูลเฉินฯ: https://www.dhakulchan.net/page/about-dhakulchan`;
            }

            return { message: message, data: data };
        } else {
            throw new Error(data.error || 'Failed to generate secure URL');
        }
    } catch (error) {
        console.error('❌ Error generating enhanced message:', error);
        throw error;
    }
}

/**
 * Open public share page for booking
 * @param {number} bookingId Booking ID
 * @param {string} type Document type (optional)
 */
async function openSharePage(bookingId, type = '') {
    try {
        showToast('🔄 Generating secure share page...', 'info');
        const { data } = await generateEnhancedMessage(bookingId);
        window.open(data.secure_url, '_blank');
        showToast('🌐 Opening public share page...', 'success');
    } catch (error) {
        console.error('❌ Error opening share page:', error);
        showToast('❌ Error opening share page: ' + error.message, 'error');
    }
}

/**
 * Share to social media platforms
 * @param {number} bookingId Booking ID
 * @param {string} type Document type (optional)
 */
async function shareToSocialMedia(bookingId, type = '') {
    try {
        showToast('🔄 Preparing public page share...', 'info');
        const { message, data } = await generateEnhancedMessage(bookingId);

        // สร้างข้อความแบบใหม่ (สั้นกว่าเดิม)
        const shortMessage = `สวัสดีค่ะ
บริษัท ตระกูลเฉินฯ แจ้งรายละเอียดบริการหรือรายการทัวร์ หมายเลขอ้างอิง ${data.booking_reference}
กรุณาคลิกดูรายละเอียดตามลิงค์ด้านล่างค่ะ

📋 Service Proposal-Travel Service: ${data.secure_url}

ติดต่อสอบถามข้อมูลเพิ่มเติม:
📞 Tel: BKK +662 2744216  📞 Tel: HKG +852 23921155
📧 Email: booking@dhakulchan.com
📱 Line OA: @dhakulchan | @changuru
🏛️ รู้จักตระกูลเฉินฯ: https://www.dhakulchan.net/page/about-dhakulchan`;

        if (navigator.share) {
            await navigator.share({
                title: `${data.document_title} - ${data.booking_reference}`,
                text: shortMessage,
                url: data.secure_url
            });
            showToast('📱 Shared successfully!', 'success');
        } else {
            // Fallback for browsers without Web Share API
            await copyToClipboard(shortMessage);
            showToast('📋 Share content copied to clipboard!', 'success');
        }
    } catch (error) {
        console.error('❌ Error sharing:', error);
        showToast('❌ Error sharing: ' + error.message, 'error');
    }
}

/**
 * Share to LINE OA with booking message
 * @param {number} bookingId Booking ID
 */
async function shareToLineOA(bookingId) {
    try {
        showToast('🔄 Preparing Line OA message...', 'info');
        const { message } = await generateEnhancedMessage(bookingId);

        // Open Line with pre-filled message
        const lineUrl = `https://line.me/R/msg/text/?${encodeURIComponent(message)}`;
        window.open(lineUrl, '_blank');

        showToast('📱 Opening Line OA...', 'success');
    } catch (error) {
        console.error('❌ Error opening Line OA:', error);
        showToast('❌ Error opening Line OA: ' + error.message, 'error');
    }
}

/**
 * Copy LINE message to clipboard
 * @param {number} bookingId Booking ID
 */
async function copyLineMessage(bookingId) {
    try {
        showToast('🔄 Generating Line message...', 'info');
        const { message } = await generateEnhancedMessage(bookingId);
        await copyToClipboard(message);
        showToast('✅ Line message copied to clipboard!', 'success');
    } catch (error) {
        console.error('❌ Copy Line message error:', error);
        showToast('❌ Error copying message: ' + error.message, 'error');
    }
}

/**
 * Share public link
 * @param {number} bookingId Booking ID
 * @param {Event} event Click event
 */
async function sharePublic(bookingId, event) {
    try {
        event.preventDefault();
        showToast('🔄 Generating public share link...', 'info');
        const { data } = await generateEnhancedMessage(bookingId);

        if (navigator.share) {
            await navigator.share({
                title: `${data.document_title} - ${data.booking_reference}`,
                url: data.secure_url
            });
            showToast('📱 Shared successfully!', 'success');
        } else {
            await copyToClipboard(data.secure_url);
            showToast('📋 Public link copied to clipboard!', 'success');
        }
    } catch (error) {
        console.error('❌ Share public error:', error);
        showToast('❌ Error sharing public link: ' + error.message, 'error');
    }
}

/**
 * Reset share token for booking
 * @param {number} bookingId Booking ID
 */
async function resetShareToken(bookingId) {
    try {
        showToast('🔄 Resetting share token...', 'info');
        const response = await fetch(`/api/booking/${bookingId}/reset-share-token`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include'
        });
        const data = await response.json();

        if (data.success) {
            showToast('✅ Share token reset successfully!', 'success');
            // Reload page to show new token
            setTimeout(() => location.reload(), 1000);
        } else {
            showToast('❌ Failed to reset share token', 'error');
        }
    } catch (error) {
        showToast('❌ Error resetting share token: ' + error.message, 'error');
    }
}

/**
 * Lock share token for booking
 * @param {number} bookingId Booking ID
 */
async function lockShareToken(bookingId) {
    try {
        showToast('🔄 Locking share token...', 'info');
        const response = await fetch(`/api/booking/${bookingId}/lock-share-token`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include'
        });
        const data = await response.json();

        if (data.success) {
            showToast('🔒 Share token locked successfully!', 'success');
            // Reload page to show locked status
            setTimeout(() => location.reload(), 1000);
        } else {
            showToast('❌ Failed to lock share token', 'error');
        }
    } catch (error) {
        showToast('❌ Error locking share token: ' + error.message, 'error');
    }
}

/**
 * Send enhanced message to LINE OA
 * @param {number} bookingId Booking ID
 */
async function sendToLineOA(bookingId) {
    try {
        showToast('🔄 Preparing Line OA message...', 'info');
        const { message } = await generateEnhancedMessage(bookingId);

        // Open Line with pre-filled message
        const lineUrl = `https://line.me/R/msg/text/?${encodeURIComponent(message)}`;
        window.open(lineUrl, '_blank');

        showToast('📱 Opening Line OA...', 'success');
    } catch (error) {
        showToast('❌ Error opening Line OA: ' + error.message, 'error');
    }
}

/**
 * Copy enhanced message to clipboard
 * @param {number} bookingId Booking ID
 */
async function copyEnhancedMessage(bookingId) {
    try {
        console.log('🎯 Copy Message button clicked for booking:', bookingId);
        showToast('🔄 Generating secure message...', 'info');
        const { message } = await generateEnhancedMessage(bookingId);
        console.log('📝 Message generated:', message);

        if (navigator.clipboard) {
            await navigator.clipboard.writeText(message);
            showToast('✅ Message copied to clipboard!', 'success');
            console.log('✅ Message copied via navigator.clipboard');
        } else {
            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = message;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            showToast('✅ Message copied to clipboard!', 'success');
            console.log('✅ Message copied via fallback method');
        }
    } catch (error) {
        console.error('❌ Copy message error:', error);
        showToast('❌ Error copying message: ' + error.message, 'error');
    }
}

/**
 * Open public share page (alias for openSharePage)
 * @param {number} bookingId Booking ID
 */
async function openPublicSharePage(bookingId) {
    return await openSharePage(bookingId);
}

/**
 * Send email with link message
 * @param {number} bookingId Booking ID
 */
async function emailLinkMessage(bookingId) {
    try {
        console.log('🎯 Email Link-Message button clicked for booking:', bookingId);
        showToast('🔄 Preparing to send email...', 'info');

        // Prompt user for email address
        const email = prompt('Enter email address to send the booking link:');
        if (!email) {
            showToast('📧 Email sending cancelled', 'info');
            return;
        }

        // Validate email format
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(email)) {
            showToast('❌ Please enter a valid email address', 'error');
            return;
        }

        console.log('📧 Sending email to:', email);
        showToast('📧 Sending email...', 'info');

        // Send email via API
        const response = await fetch(`/api/share/booking/${bookingId}/send-email`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include',  // Include cookies for authentication
            body: JSON.stringify({ email: email })
        });

        console.log('📡 Email API response:', response.status, response.statusText);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        console.log('📧 Email response data:', data);

        if (data.success) {
            showToast(`✅ Email sent successfully to ${email}!`, 'success');
        } else {
            showToast(`❌ Failed to send email: ${data.error}`, 'error');
        }
    } catch (error) {
        console.error('❌ Email error:', error);
        showToast('❌ Error sending email: ' + error.message, 'error');
    }
}

/**
 * Get share status for booking
 * @param {number} bookingId Booking ID
 */
async function getShareStatus(bookingId) {
    try {
        console.log('🎯 Share Status button clicked for booking:', bookingId);
        showToast('🔄 Checking share status...', 'info');
        const response = await fetch(`/api/share/booking/${bookingId}/status`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include'  // Include cookies for authentication
        });
        console.log('📡 Share status response:', response.status, response.statusText);

        if (!response.ok) {
            if (response.status === 401) {
                throw new Error('Please login to access this feature');
            } else {
                const errorText = await response.text();
                throw new Error(`HTTP ${response.status}: ${errorText}`);
            }
        }

        const data = await response.json();
        console.log('📊 Share status data:', data);

        if (data.success) {
            showToast(`📊 Shares: ${data.share_count || 0} | Views: ${data.view_count || 0}`, 'info');
        } else {
            showToast('❌ Could not get share status: ' + (data.error || 'Unknown error'), 'error');
        }
    } catch (error) {
        console.error('❌ Share status error:', error);
        showToast('❌ Error getting share status: ' + error.message, 'error');
    }
}

/**
 * Initialize on DOM ready
 */
document.addEventListener('DOMContentLoaded', function () {
    initializeBookingData();

    // Add CSS animations for toasts
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideInRight {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        
        @keyframes slideOutRight {
            from { transform: translateX(0); opacity: 1; }
            to { transform: translateX(100%); opacity: 0; }
        }
        
        .toast-notification {
            transition: all 0.3s ease;
        }
        
        .toast-notification:hover {
            transform: scale(1.02);
        }
    `;
    document.head.appendChild(style);

    console.log('Enhanced Booking JavaScript loaded successfully');
});