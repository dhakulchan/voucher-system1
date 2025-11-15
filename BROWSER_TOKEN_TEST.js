// Browser Console Test Script for Token-based Sharing
// Open http://localhost:5001/booking/view/174 and paste this in console

console.log("🔐 Testing Token-based Sharing System in Browser...");

// Test Copy Line Message with Token
console.log("\n📋 Testing Copy Line Message with Token...");
fetch('/api/share/booking/174/url')
    .then(response => {
        console.log('API Response Status:', response.status);
        return response.json();
    })
    .then(data => {
        console.log('✅ Copy Line Message API Response:', data);

        if (data.success) {
            const secureUrl = data.secure_url;
            const bookingRef = data.booking_reference;

            const message = `สวัสดีครับ 
ต้องการสอบถามเรื่องการจอง ${bookingRef}

📋 Service Proposal: ${secureUrl}
🖼️ Download PNG: ${secureUrl}/png
📄 Download PDF: ${secureUrl}/pdf

📞 Tel: +662 2744216
📧 Email: support@dhakulchan.com
📱 Line OA: @dhakulchan`;

            console.log('📋 Generated Message:', message);
            console.log('🔗 Secure URL:', secureUrl);
        }
    })
    .catch(error => console.error('❌ Copy Line Message Error:', error));

// Test Share Public Link with Token
console.log("\n🔗 Testing Share Public Link with Token...");
fetch('/api/share/booking/174/url')
    .then(response => response.json())
    .then(data => {
        console.log('✅ Share Public API Response:', data);

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

            console.log('📤 Generated Share Message:', shareMessage);
        }
    })
    .catch(error => console.error('❌ Share Public Error:', error));

// Test if secure URL can be accessed publicly
setTimeout(() => {
    console.log("\n🌐 Testing if secure URLs work...");
    fetch('/api/share/booking/174/url')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const secureUrl = data.secure_url;
                console.log('🔗 Testing secure URL access:', secureUrl);

                // Try to access the secure URL
                fetch(secureUrl.replace(window.location.origin, ''))
                    .then(response => {
                        if (response.ok) {
                            console.log('✅ Secure URL accessible!');
                        } else {
                            console.log('❌ Secure URL not accessible:', response.status);
                        }
                    });
            }
        });
}, 2000);

console.log("✅ Token-based sharing test completed. Check results above.");
