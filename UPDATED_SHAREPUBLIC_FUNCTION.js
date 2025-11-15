window.sharePublic = function (bookingId) {
    // ดึง secure URL แล้วแชร์ผ่าน Web Share API หรือ clipboard
    fetch(`/api/share/booking/${bookingId}/url`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const secureUrl = data.secure_url;
                const bookingRef = data.booking_reference;

                const shareMessage = `📋 Service Proposal - Booking ${bookingRef}

🔗 View Details: ${secureUrl}
🖼️ Download PNG: ${secureUrl}/png  
📄 Download PDF: ${secureUrl}/pdf

📞 Contact us:
Tel: +662 2744216
Email: support@dhakulchan.com
Line OA: @dhakulchan

🔒 Secure link with 7-day expiration`;

                // Try Web Share API first
                if (navigator.share && /Android|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)) {
                    navigator.share({
                        title: `Service Proposal - ${bookingRef}`,
                        text: shareMessage,
                        url: secureUrl
                    }).then(() => {
                        showToast('📤 แชร์ Service Proposal แล้ว', 'success');
                    }).catch(() => {
                        copySecureLinkFallback(shareMessage);
                    });
                } else {
                    // Fallback to clipboard copy
                    copySecureLinkFallback(shareMessage);
                }
            } else {
                showToast('❌ ไม่สามารถสร้างลิงก์แชร์ได้', 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showToast('❌ เกิดข้อผิดพลาดในการสร้างลิงก์', 'error');
        });
};
