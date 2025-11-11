// Date format handlers for create booking form
document.addEventListener('DOMContentLoaded', function () {
    // Make formatDateForDisplay and parseDateFromDisplay globally available
    if (typeof window.formatDateForDisplay === 'undefined') {
        window.formatDateForDisplay = function (dateStr, includeTime = false) {
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
        };
    }

    if (typeof window.parseDateFromDisplay === 'undefined') {
        window.parseDateFromDisplay = function (displayStr, includeTime = false) {
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
        };
    }

    // Use global functions with fallback
    const formatDateForDisplay = window.formatDateForDisplay;
    const parseDateFromDisplay = window.parseDateFromDisplay;
    // Arrival Date field
    const arrivalDateDisplay = document.getElementById('arrival_date_display');
    const arrivalDateHidden = document.getElementById('arrival_date');

    if (arrivalDateDisplay && arrivalDateHidden) {
        arrivalDateDisplay.addEventListener('input', function () {
            const convertedValue = parseDateFromDisplay(this.value, false);
            arrivalDateHidden.value = convertedValue;

            // Auto-update all dependent dates
            window.validateDateRange();
        });

        arrivalDateDisplay.addEventListener('blur', function () {
            const convertedValue = parseDateFromDisplay(this.value, false);
            if (convertedValue && this.value) {
                const reformatted = formatDateForDisplay(convertedValue, false);
                this.value = reformatted;
                arrivalDateHidden.value = convertedValue;

                // Validate and update all dependent dates
                window.validateDateRange();
            }
        });
    }

    // Departure Date field with smart suggestions
    const departureDateDisplay = document.getElementById('departure_date_display');
    const departureDateHidden = document.getElementById('departure_date');

    if (departureDateDisplay && departureDateHidden) {
        departureDateDisplay.addEventListener('input', function () {
            const convertedValue = parseDateFromDisplay(this.value, false);
            departureDateHidden.value = convertedValue;
        });

        departureDateDisplay.addEventListener('blur', function () {
            const convertedValue = parseDateFromDisplay(this.value, false);
            if (convertedValue && this.value) {
                const reformatted = formatDateForDisplay(convertedValue, false);
                this.value = reformatted;
                departureDateHidden.value = convertedValue;

                // Validate date range
                window.validateDateRange();
            }
        });

        // Add click helper for departure date
        departureDateDisplay.addEventListener('focus', function () {
            const arrivalDate = arrivalDateHidden ? arrivalDateHidden.value : '';
            const departureDate = departureDateHidden ? departureDateHidden.value : '';

            // If departure date equals arrival date, show hint for multi-day trip
            if (arrivalDate && departureDate && arrivalDate === departureDate) {
                console.log('Tip: Same-day trip selected. Double-click to extend to next day.');
            }
        });

        // Double-click to extend to next day
        departureDateDisplay.addEventListener('dblclick', function () {
            const arrivalDate = arrivalDateHidden ? arrivalDateHidden.value : '';
            if (arrivalDate) {
                const arrivalDateObj = new Date(arrivalDate);
                const nextDay = new Date(arrivalDateObj);
                nextDay.setDate(arrivalDateObj.getDate() + 1);

                const nextDayStr = nextDay.toISOString().split('T')[0];
                departureDateHidden.value = nextDayStr;

                const displayValue = formatDateForDisplay(nextDayStr, false);
                this.value = displayValue;

                console.log('Extended to next day:', nextDayStr, '-> Display:', displayValue);
            }
        });
    }

    // Enhanced date range validation function (make it global)
    window.validateDateRange = function (forceNextDay = false) {
        const arrivalDate = arrivalDateHidden ? arrivalDateHidden.value : '';
        const departureDate = departureDateHidden ? departureDateHidden.value : '';

        if (arrivalDate && (!departureDate || new Date(departureDate) < new Date(arrivalDate))) {
            const arrivalDateObj = new Date(arrivalDate);
            let newDepartureDate;

            if (forceNextDay) {
                // Force next day for certain scenarios
                const nextDay = new Date(arrivalDateObj);
                nextDay.setDate(arrivalDateObj.getDate() + 1);
                newDepartureDate = nextDay.toISOString().split('T')[0];
            } else {
                // Default: same day (allows same-day trips)
                newDepartureDate = arrivalDateObj.toISOString().split('T')[0];
            }

            departureDateHidden.value = newDepartureDate;

            if (departureDateDisplay) {
                const displayValue = formatDateForDisplay(newDepartureDate, false);
                departureDateDisplay.value = displayValue;
            }

            const dayType = forceNextDay ? 'next day' : 'same day';
            console.log(`Auto-updated departure date (${dayType}):`, newDepartureDate, '-> Display:', formatDateForDisplay(newDepartureDate, false));
        }

        // Auto-update Time Limit and Due Date to match or exceed arrival date
        validateTimeLimitAndDueDate();
    };

    // Validate Time Limit and Due Date against arrival date
    window.validateTimeLimitAndDueDate = function () {
        const arrivalDate = arrivalDateHidden ? arrivalDateHidden.value : '';

        if (arrivalDate) {
            const arrivalDateObj = new Date(arrivalDate);

            // Update Time Limit if it's before arrival date or empty
            const timeLimitDate = timeLimitHidden ? timeLimitHidden.value : '';
            if (!timeLimitDate || (timeLimitDate && new Date(timeLimitDate.split('T')[0]) < arrivalDateObj)) {
                // Set Time Limit to arrival date with default time (end of day)
                const defaultTime = '23:59';
                const newTimeLimit = `${arrivalDate}T${defaultTime}`;

                if (timeLimitHidden) {
                    timeLimitHidden.value = newTimeLimit;
                }

                if (timeLimitDisplay) {
                    const displayValue = formatDateForDisplay(newTimeLimit, true);
                    timeLimitDisplay.value = displayValue;
                    console.log('Auto-updated Time Limit:', newTimeLimit, '-> Display:', displayValue);
                }
            }

            // Update Due Date if it's before arrival date or empty
            const dueDate = dueDateHidden ? dueDateHidden.value : '';
            if (!dueDate || (dueDate && new Date(dueDate) < arrivalDateObj)) {
                // Set Due Date to arrival date
                const newDueDate = arrivalDate;

                if (dueDateHidden) {
                    dueDateHidden.value = newDueDate;
                }

                if (dueDateDisplay) {
                    const displayValue = formatDateForDisplay(newDueDate, false);
                    dueDateDisplay.value = displayValue;
                    console.log('Auto-updated Due Date:', newDueDate, '-> Display:', displayValue);
                }
            }
        }
    };

    // Listen for custom dateUpdated events from calendar picker
    document.addEventListener('dateUpdated', function (event) {
        console.log('Date updated event received:', event.detail.fieldId);

        if (event.detail.fieldId === 'arrival_date') {
            // Update all dependent dates when arrival date changes
            window.validateDateRange();
        } else if (event.detail.fieldId === 'departure_date') {
            // Only validate departure date
            window.validateDateRange();
        } else if (event.detail.fieldId === 'time_limit' || event.detail.fieldId === 'due_date') {
            // Validate Time Limit and Due Date against arrival date
            window.validateTimeLimitAndDueDate();
        }
    });

    // Set default dates on page load
    function setDefaultDates() {
        // Skip setting default dates for create form (it has its own logic)
        if (window.location.pathname.includes('/booking/create')) {
            console.log('Skipping setDefaultDates for create form - using custom logic instead');
            return;
        }

        console.log('setDefaultDates called - checking fields...');
        console.log('arrivalDateHidden:', arrivalDateHidden);
        console.log('departureDateHidden:', departureDateHidden);
        console.log('arrivalDateDisplay:', arrivalDateDisplay);
        console.log('departureDateDisplay:', departureDateDisplay);

        // Set default arrival date to today if empty
        if (arrivalDateHidden && !arrivalDateHidden.value) {
            const today = new Date();
            const todayStr = today.toISOString().split('T')[0];
            arrivalDateHidden.value = todayStr;

            if (arrivalDateDisplay) {
                const displayValue = formatDateForDisplay(todayStr, false);
                arrivalDateDisplay.value = displayValue;
                console.log('Set default arrival date:', todayStr, '-> Display:', displayValue);
            }
        } else if (arrivalDateHidden && arrivalDateHidden.value) {
            // Format existing value for display
            if (arrivalDateDisplay && !arrivalDateDisplay.value) {
                const displayValue = formatDateForDisplay(arrivalDateHidden.value, false);
                arrivalDateDisplay.value = displayValue;
                console.log('Format existing arrival date:', arrivalDateHidden.value, '-> Display:', displayValue);
            }
        }

        // Set default departure date to same as arrival date if empty (same-day trip)
        if (departureDateHidden && !departureDateHidden.value && arrivalDateHidden && arrivalDateHidden.value) {
            const sameDayDate = arrivalDateHidden.value;
            departureDateHidden.value = sameDayDate;

            if (departureDateDisplay) {
                const displayValue = formatDateForDisplay(sameDayDate, false);
                departureDateDisplay.value = displayValue;
                console.log('Set default departure date (same day):', sameDayDate, '-> Display:', displayValue);
            }
        } else if (departureDateHidden && departureDateHidden.value) {
            // Format existing value for display
            if (departureDateDisplay && !departureDateDisplay.value) {
                const displayValue = formatDateForDisplay(departureDateHidden.value, false);
                departureDateDisplay.value = displayValue;
                console.log('Format existing departure date:', departureDateHidden.value, '-> Display:', displayValue);
            }
        }

        // Set default Time Limit to tomorrow (today + 1) if empty
        if (timeLimitHidden && !timeLimitHidden.value) {
            const today = new Date();
            const tomorrow = new Date(today);
            tomorrow.setDate(today.getDate() + 1);
            const tomorrowStr = tomorrow.toISOString().split('T')[0];
            const defaultTimeLimit = `${tomorrowStr}T23:59`; // End of tomorrow
            timeLimitHidden.value = defaultTimeLimit;

            if (timeLimitDisplay) {
                const displayValue = formatDateForDisplay(defaultTimeLimit, true);
                timeLimitDisplay.value = displayValue;
                console.log('Set default Time Limit (tomorrow):', defaultTimeLimit, '-> Display:', displayValue);
            }
        }

        // Set default Due Date to tomorrow (today + 1) if empty
        if (dueDateHidden && !dueDateHidden.value) {
            const today = new Date();
            const tomorrow = new Date(today);
            tomorrow.setDate(today.getDate() + 1);
            const tomorrowStr = tomorrow.toISOString().split('T')[0];
            dueDateHidden.value = tomorrowStr;

            if (dueDateDisplay) {
                const displayValue = formatDateForDisplay(tomorrowStr, false);
                dueDateDisplay.value = displayValue;
                console.log('Set default Due Date (tomorrow):', tomorrowStr, '-> Display:', displayValue);
            }
        }

        // Validate and set all dates (in case there are any conflicts)
        window.validateDateRange();
    }

    // Initialize default dates
    setTimeout(setDefaultDates, 100);

    // Time Limit field with validation
    const timeLimitDisplay = document.getElementById('time_limit_display');
    const timeLimitHidden = document.getElementById('time_limit');

    if (timeLimitDisplay && timeLimitHidden) {
        timeLimitDisplay.addEventListener('input', function () {
            const convertedValue = parseDateFromDisplay(this.value, true);
            timeLimitHidden.value = convertedValue;
        });

        timeLimitDisplay.addEventListener('blur', function () {
            const convertedValue = parseDateFromDisplay(this.value, true);
            if (convertedValue && this.value) {
                const reformatted = formatDateForDisplay(convertedValue, true);
                this.value = reformatted;
                timeLimitHidden.value = convertedValue;

                // Validate against arrival date
                window.validateTimeLimitAndDueDate();
            }
        });
    }

    // Due Date field with validation
    const dueDateDisplay = document.getElementById('due_date_display');
    const dueDateHidden = document.getElementById('due_date');

    if (dueDateDisplay && dueDateHidden) {
        dueDateDisplay.addEventListener('input', function () {
            const convertedValue = parseDateFromDisplay(this.value, false);
            dueDateHidden.value = convertedValue;
        });

        dueDateDisplay.addEventListener('blur', function () {
            const convertedValue = parseDateFromDisplay(this.value, false);
            if (convertedValue && this.value) {
                const reformatted = formatDateForDisplay(convertedValue, false);
                this.value = reformatted;
                dueDateHidden.value = convertedValue;

                // Validate against arrival date
                window.validateTimeLimitAndDueDate();
            }
        });
    }
});
