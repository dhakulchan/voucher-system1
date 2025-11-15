// Complete Updated sharePublic Function with 30-day expiration
window.sharePublic = async function (bookingId) {
    try {
        // Get button element and show loading state
        const button = event ? event.target : document.querySelector(`[onclick*="sharePublic('${bookingId}')"]`);
        const originalText = button ? button.textContent : 'Share Public Message';

        if (button) {
            button.textContent = '🔄 สร้างลิงก์แชร์...';
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
📧 Email: support@dhakulchan.com
📱 Line OA: @dhakulchan

🔒 Secure link (expires in ${expiryDays} days)`;

            // Try native sharing first (mobile/modern browsers)
            if (navigator.share && /Android|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)) {
                try {
                    await navigator.share({
                        title: `Service Proposal - ${bookingRef}`,
                        text: shareMessage,
                        url: secureUrl
                    });
                    showToast('📤 แชร์ Service Proposal เรียบร้อยแล้ว!', 'success');
                    return;
                } catch (shareError) {
                    // User cancelled or share failed, fall back to clipboard
                    console.log('Native share cancelled or failed:', shareError);
                }
            }

            // Fallback: Copy to clipboard
            try {
                await navigator.clipboard.writeText(shareMessage);
                showToast('📋 คัดลอกลิงก์แชร์ไปยัง clipboard แล้ว!', 'success');

                // Optional: Also open the link in new tab
                window.open(secureUrl, '_blank');

            } catch (clipboardError) {
                // Fallback for older browsers
                const textArea = document.createElement('textarea');
                textArea.value = shareMessage;
                document.body.appendChild(textArea);
                textArea.select();

                try {
                    document.execCommand('copy');
                    showToast('📋 คัดลอกลิงก์แชร์เรียบร้อยแล้ว!', 'success');
                    window.open(secureUrl, '_blank');
                } catch (err) {
                    // Final fallback - just open the link
                    window.open(secureUrl, '_blank');
                    showToast('🔗 เปิดลิงก์แชร์ในแท็บใหม่แล้ว', 'info');
                }

                document.body.removeChild(textArea);
            }

        } else {
            throw new Error(data.message || 'ไม่สามารถสร้างลิงก์แชร์ได้');
        }

    } catch (error) {
        console.error('Share error:', error);
        showToast(`❌ เกิดข้อผิดพลาด: ${error.message}`, 'error');
    } finally {
        // Restore button state
        if (button) {
            button.textContent = originalText;
            button.disabled = false;
        }
    }
};
