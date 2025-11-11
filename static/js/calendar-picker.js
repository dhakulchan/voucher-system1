// Alternative approach: Replace display input with actual date/datetime input temporarily
function showDatePicker(fieldId) {
    console.log('showDatePicker called with:', fieldId);
    const hiddenInput = document.getElementById(fieldId);
    const displayInput = document.getElementById(fieldId + '_display');

    if (!hiddenInput || !displayInput) {
        console.error('Fields not found:', fieldId);
        return;
    }

    // Convert the display input to a date input temporarily
    const originalType = displayInput.type;
    const originalValue = displayInput.value;

    // Convert display value to date format if needed
    let dateValue = hiddenInput.value;
    if (!dateValue && originalValue) {
        dateValue = parseDateFromDisplay(originalValue, false);
    }

    // Change to date input
    displayInput.type = 'date';
    displayInput.value = dateValue;
    displayInput.style.color = '#000';

    // Focus and attempt to show picker
    setTimeout(() => {
        displayInput.focus();
        displayInput.click();
        if (displayInput.showPicker) {
            try {
                displayInput.showPicker();
            } catch (e) {
                console.log('showPicker not supported:', e);
            }
        }
    }, 100);

    // Handle value change
    const handleChange = function () {
        if (displayInput.value) {
            hiddenInput.value = displayInput.value;
            const displayValue = formatDateForDisplay(displayInput.value, false);

            // Switch back to text input and show formatted value
            displayInput.type = 'text';
            displayInput.value = displayValue;
            displayInput.style.color = '';

            console.log('Date selected:', hiddenInput.value, '-> Display:', displayValue);

            // Trigger date range validation if this is arrival or departure date
            if (fieldId === 'arrival_date' || fieldId === 'departure_date') {
                // Wait a bit for the DOM to update, then trigger validation
                setTimeout(() => {
                    if (typeof validateDateRange === 'function') {
                        validateDateRange();
                    } else {
                        // Fallback: trigger a custom event that date-handlers.js can listen to
                        const event = new CustomEvent('dateUpdated', { detail: { fieldId: fieldId } });
                        document.dispatchEvent(event);
                    }
                }, 50);
            }
        }
        displayInput.removeEventListener('change', handleChange);
        displayInput.removeEventListener('blur', handleBlur);
    };

    const handleBlur = function () {
        setTimeout(() => {
            // If no value was selected, revert back
            if (!displayInput.value || displayInput.type === 'date') {
                displayInput.type = 'text';
                displayInput.value = originalValue;
                displayInput.style.color = '';
            }
            displayInput.removeEventListener('change', handleChange);
            displayInput.removeEventListener('blur', handleBlur);
        }, 200);
    };

    displayInput.addEventListener('change', handleChange);
    displayInput.addEventListener('blur', handleBlur);
}

function showDateTimePicker(fieldId) {
    console.log('showDateTimePicker called with:', fieldId);
    const hiddenInput = document.getElementById(fieldId);
    const displayInput = document.getElementById(fieldId + '_display');

    if (!hiddenInput || !displayInput) {
        console.error('Fields not found:', fieldId);
        return;
    }

    // Store original values
    const originalType = displayInput.type;
    const originalValue = displayInput.value;
    const originalPlaceholder = displayInput.placeholder;

    // Convert display value to datetime format if needed
    let dateValue = hiddenInput.value;
    if (!dateValue && originalValue) {
        dateValue = parseDateFromDisplay(originalValue, true);
    }

    // Set current datetime if no value
    if (!dateValue) {
        const now = new Date();
        const year = now.getFullYear();
        const month = String(now.getMonth() + 1).padStart(2, '0');
        const day = String(now.getDate()).padStart(2, '0');
        const hour = String(now.getHours()).padStart(2, '0');
        const minute = String(now.getMinutes()).padStart(2, '0');
        dateValue = `${year}-${month}-${day}T${hour}:${minute}`;
    }

    // Change to datetime-local input
    displayInput.type = 'datetime-local';
    displayInput.value = dateValue;
    displayInput.style.color = '#000';
    displayInput.placeholder = '';
    displayInput.style.fontSize = '14px';

    // Create overlay to ensure focus
    const overlay = document.createElement('div');
    overlay.style.position = 'fixed';
    overlay.style.top = '0';
    overlay.style.left = '0';
    overlay.style.width = '100vw';
    overlay.style.height = '100vh';
    overlay.style.backgroundColor = 'rgba(0,0,0,0.1)';
    overlay.style.zIndex = '9998';
    overlay.style.display = 'flex';
    overlay.style.alignItems = 'center';
    overlay.style.justifyContent = 'center';

    document.body.appendChild(overlay);

    // Focus and attempt to show picker
    setTimeout(() => {
        displayInput.focus();
        displayInput.select();

        // Try multiple methods to trigger picker
        setTimeout(() => {
            if (displayInput.showPicker) {
                try {
                    displayInput.showPicker();
                    console.log('showPicker() called successfully');
                } catch (e) {
                    console.log('showPicker failed, trying click:', e);
                    displayInput.click();
                }
            } else {
                console.log('showPicker not available, using click');
                displayInput.click();
            }
        }, 50);
    }, 100);

    // Handle value change
    const handleChange = function () {
        console.log('DateTime picker value changed:', displayInput.value);
        if (displayInput.value) {
            hiddenInput.value = displayInput.value;
            const displayValue = formatDateForDisplay(displayInput.value, true);

            // Switch back to text input and show formatted value
            displayInput.type = 'text';
            displayInput.value = displayValue;
            displayInput.style.color = '';
            displayInput.placeholder = originalPlaceholder;
            displayInput.style.fontSize = '';

            console.log('DateTime selected:', hiddenInput.value, '-> Display:', displayValue);
        }

        // Remove overlay and cleanup
        if (document.body.contains(overlay)) {
            document.body.removeChild(overlay);
        }
        displayInput.removeEventListener('change', handleChange);
        displayInput.removeEventListener('blur', handleBlur);
    };

    const handleBlur = function () {
        setTimeout(() => {
            console.log('DateTime picker blur event');
            // If no value was selected, revert back
            if (!displayInput.value || displayInput.type === 'datetime-local') {
                displayInput.type = 'text';
                displayInput.value = originalValue;
                displayInput.style.color = '';
                displayInput.placeholder = originalPlaceholder;
                displayInput.style.fontSize = '';
            }

            // Remove overlay and cleanup
            if (document.body.contains(overlay)) {
                document.body.removeChild(overlay);
            }
            displayInput.removeEventListener('change', handleChange);
            displayInput.removeEventListener('blur', handleBlur);
        }, 200);
    };

    // Close on overlay click
    overlay.addEventListener('click', function (e) {
        if (e.target === overlay) {
            handleBlur();
        }
    });

    displayInput.addEventListener('change', handleChange);
    displayInput.addEventListener('blur', handleBlur);
}

// Date format conversion functions
function formatDateForDisplay(dateStr, includeTime = false) {
    if (!dateStr) return '';
    try {
        if (includeTime) {
            // For datetime-local format: YYYY-MM-DDTHH:MM
            // Format as DD/MM/YYYY HH:MM for Time Limit
            const [datePart, timePart] = dateStr.split('T');
            const [year, month, day] = datePart.split('-');
            const [hour, minute] = timePart ? timePart.split(':') : ['00', '00'];
            return `${day}/${month}/${year} ${hour}:${minute}`;
        } else {
            // For date format: YYYY-MM-DD
            // Format as DD/MM/YYYY for regular dates
            const [year, month, day] = dateStr.split('-');
            return `${day}/${month}/${year}`;
        }
    } catch (e) {
        return dateStr;
    }
}

function parseDateFromDisplay(displayStr, includeTime = false) {
    if (!displayStr) return '';
    try {
        if (includeTime) {
            // Parse DD/MM/YYYY HH:MM format for Time Limit
            const [datePart, timePart] = displayStr.split(' ');
            const [day, month, year] = datePart.split('/');
            const [hour, minute] = timePart ? timePart.split(':') : ['00', '00'];
            return `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}T${hour.padStart(2, '0')}:${minute.padStart(2, '0')}`;
        } else {
            // Parse DD/MM/YYYY format for regular dates
            const [day, month, year] = displayStr.split('/');
            return `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`;
        }
    } catch (e) {
        return '';
    }
}
