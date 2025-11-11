/**
 * Enhanced Booking System JavaScript - Extracted from Template
 * This file is separated to prevent Jinja2/JavaScript corruption issues
 */

// Booking data will be injected by template
window.BOOKING_DATA = window.BOOKING_DATA || {};

/**
 * Get current booking ID safely
 * @returns {number} Current booking ID
 */
function getCurrentBookingId() {
    // Try multiple sources for booking ID
    const bookingData = document.getElementById('booking-data');
    if (bookingData && bookingData.dataset.bookingId) {
        return parseInt(bookingData.dataset.bookingId);
    }

    // Fallback to global data
    if (window.BOOKING_DATA && window.BOOKING_DATA.id) {
        return parseInt(window.BOOKING_DATA.id);
    }

    // Last resort: parse from URL
    const urlMatch = window.location.pathname.match(/\/booking\/view\/(\d+)/);
    if (urlMatch) {
        return parseInt(urlMatch[1]);
    }

    console.error('Could not determine booking ID');
    return null;
}

/**
 * Initialize booking data from template injection
 * This function will be called by the template
 */
function initializeBookingData(bookingId, bookingReference, status) {
    window.BOOKING_DATA = {
        id: bookingId,
        reference: bookingReference,
        status: status
    };

    console.log('Booking data initialized:', window.BOOKING_DATA);
}

/**
 * Enhanced toast notification with better styling
 */
function showToast(message, type = 'info', duration = 5000) {
    // Remove existing toasts
    const existingToasts = document.querySelectorAll('.enhanced-toast');
    existingToasts.forEach(toast => toast.remove());

    // Create toast element
    const toast = document.createElement('div');
    toast.className = `enhanced-toast alert alert-${type === 'success' ? 'success' : type === 'error' ? 'danger' : 'info'} d-flex align-items-center`;
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 9999;
        min-width: 300px;
        animation: slideInRight 0.3s ease-out;
    `;

    // Add icon based on type
    const icon = type === 'success' ? 'fas fa-check-circle' :
        type === 'error' ? 'fas fa-exclamation-circle' :
            'fas fa-info-circle';

    toast.innerHTML = `
        <i class="${icon} me-2"></i>
        <span>${message}</span>
        <button type="button" class="btn-close ms-auto" onclick="this.parentElement.remove()"></button>
    `;

    document.body.appendChild(toast);

    // Auto-remove after duration
    setTimeout(() => {
        if (toast.parentElement) {
            toast.style.animation = 'slideOutRight 0.3s ease-in';
            setTimeout(() => toast.remove(), 300);
        }
    }, duration);
}

// Export functions for template use
window.getCurrentBookingId = getCurrentBookingId;
window.initializeBookingData = initializeBookingData;
window.showToast = showToast;