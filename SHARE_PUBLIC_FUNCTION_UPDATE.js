// Updated JavaScript functions for booking/view page
// Replace the existing sharePublic function with this

window.sharePublic = function (bookingId) {
    // ดึง public URL และ PNG URL จาก API
    fetch(`/api/share/booking/${bookingId}/public`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const publicUrl = data.public_url;
                const publicPngUrl = data.public_png_url;
                const bookingRef = data.booking_reference;

                // สร้างข้อความแชร์
                const shareMessage = `📋 Service Proposal - Booking ${bookingRef}

🔗 Public View: ${publicUrl}
📸 Service Proposal PNG: ${publicPngUrl}

📞 Contact us:
Tel: +662 2744216
Email: support@dhakulchan.com
Line OA: @dhakulchan`;

                // ตรวจสอบว่าเบราว์เซอร์สนับสนุน Web Share API หรือไม่
                if (navigator.share) {
                    navigator.share({
                        title: `Service Proposal - ${bookingRef}`,
                        text: shareMessage,
                        url: publicUrl
                    }).then(() => {
                        showToast('📤 แชร์สำเร็จ!', 'success');
                    }).catch((error) => {
                        console.log('Error sharing:', error);
                        // Fallback to copy to clipboard
                        copyToClipboardFallback(shareMessage);
                    });
                } else {
                    // Fallback: copy to clipboard and show options
                    copyToClipboardFallback(shareMessage);
                }
            } else {
                showToast('❌ ไม่สามารถสร้าง Public URL ได้', 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showToast('❌ เกิดข้อผิดพลาดในการสร้าง Public URL', 'error');
        });
};

// Helper function for clipboard fallback
function copyToClipboardFallback(message) {
    navigator.clipboard.writeText(message).then(() => {
        const userChoice = confirm(
            `📋 ข้อความและลิงก์คัดลอกแล้ว!\n\n` +
            `เลือกแพลตฟอร์มที่ต้องการแชร์:\n\n` +
            `✅ OK = เปิด WhatsApp\n` +
            `📧 Cancel = เปิด Email`
        );

        if (userChoice) {
            // เปิด WhatsApp
            const whatsappUrl = `https://wa.me/?text=${encodeURIComponent(message)}`;
            window.open(whatsappUrl, '_blank');
            showToast('📱 เปิด WhatsApp แล้ว กรุณาเลือกผู้รับ', 'info');
        } else {
            // เปิด Email
            const emailSubject = encodeURIComponent('Service Proposal - Booking Information');
            const emailBody = encodeURIComponent(message);
            const emailUrl = `mailto:?subject=${emailSubject}&body=${emailBody}`;
            window.open(emailUrl, '_blank');
            showToast('📧 เปิด Email แล้ว', 'info');
        }
    }).catch(() => {
        // Manual copy fallback
        const textArea = document.createElement('textarea');
        textArea.value = message;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        showToast('📋 ข้อความคัดลอกแล้ว! กรุณาไปแปะในแอปที่ต้องการแชร์', 'success');
    });
}
