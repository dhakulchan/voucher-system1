// Complete Updated copyLineMessage Function with 30-day expiration
window.copyLineMessage = async function (bookingId) {
    try {
        // Get button element and show loading state
        const button = event ? event.target : document.querySelector(`[onclick*="copyLineMessage('${bookingId}')"]`);
        const originalText = button ? button.textContent : 'Copy Line Message';

        if (button) {
            button.textContent = '🔄 สร้างข้อความ...';
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

            // Create Line message format
            const lineMessage = `สวัสดีครับ 
ต้องการสอบถามเรื่องการจอง ${bookingRef}

📋 Service Proposal: ${secureUrl}
🖼️ Download PNG: ${secureUrl}/png
📄 Download PDF: ${secureUrl}/pdf

📞 Tel: +662 2744216
📧 Email: support@dhakulchan.com
📱 Line OA: @dhakulchan

🔒 ลิงก์ปลอดภัย (หมดอายุใน ${expiryDays} วัน)`;

            // Copy to clipboard
            try {
                await navigator.clipboard.writeText(lineMessage);
                showToast('📋 คัดลอกข้อความ Line เรียบร้อยแล้ว!', 'success');

                // Optional: Generate Line URL for direct sharing
                const lineUrl = `https://line.me/R/msg/text/?${encodeURIComponent(lineMessage)}`;

                // Show option to open Line app
                setTimeout(() => {
                    if (confirm('ต้องการเปิดแอป Line เพื่อส่งข้อความหรือไม่?')) {
                        window.open(lineUrl, '_blank');
                    }
                }, 500);

            } catch (clipboardError) {
                // Fallback for older browsers
                const textArea = document.createElement('textarea');
                textArea.value = lineMessage;
                document.body.appendChild(textArea);
                textArea.select();

                try {
                    document.execCommand('copy');
                    showToast('📋 คัดลอกข้อความ Line เรียบร้อยแล้ว!', 'success');
                } catch (err) {
                    showToast('❌ ไม่สามารถคัดลอกได้ กรุณาคัดลอกด้วยตนเอง', 'error');

                    // Show message in modal or alert
                    alert(`กรุณาคัดลอกข้อความนี้:\n\n${lineMessage}`);
                }

                document.body.removeChild(textArea);
            }

        } else {
            throw new Error(data.message || 'ไม่สามารถสร้างข้อความ Line ได้');
        }

    } catch (error) {
        console.error('Copy Line Message error:', error);
        showToast(`❌ เกิดข้อผิดพลาด: ${error.message}`, 'error');
    } finally {
        // Restore button state
        if (button) {
            button.textContent = originalText;
            button.disabled = false;
        }
    }
};
