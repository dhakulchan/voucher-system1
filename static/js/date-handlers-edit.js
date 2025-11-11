// Date format handlers for edit booking form
document.addEventListener('DOMContentLoaded', function () {
    // Skip if not on edit page
    if (!window.location.pathname.includes('/edit')) {
        return;
    }

    // Get references to all date fields
    const arrivalDateDisplay = document.getElementById('arrival_date_display');
    const arrivalDateHidden = document.getElementById('arrival_date');
    const departureDateDisplay = document.getElementById('departure_date_display');
    const departureDateHidden = document.getElementById('departure_date');
    const timeLimitDisplay = document.getElementById('time_limit_display');
    const timeLimitHidden = document.getElementById('time_limit');
    const dueDateDisplay = document.getElementById('due_date_display');
    const dueDateHidden = document.getElementById('due_date');

    // Set default dates for empty fields only (don't override existing values)
    function setDefaultDatesForEdit() {
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
                console.log('Set default Time Limit (tomorrow) for edit:', defaultTimeLimit, '-> Display:', displayValue);
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
                console.log('Set default Due Date (tomorrow) for edit:', tomorrowStr, '-> Display:', displayValue);
            }
        }

        // Format existing dates for display
        if (arrivalDateHidden && arrivalDateHidden.value && arrivalDateDisplay) {
            const displayValue = formatDateForDisplay(arrivalDateHidden.value, false);
            arrivalDateDisplay.value = displayValue;
            console.log('Format existing arrival date:', arrivalDateHidden.value, '-> Display:', displayValue);
        }

        if (departureDateHidden && departureDateHidden.value && departureDateDisplay) {
            const displayValue = formatDateForDisplay(departureDateHidden.value, false);
            departureDateDisplay.value = displayValue;
            console.log('Format existing departure date:', departureDateHidden.value, '-> Display:', displayValue);
        }

        if (timeLimitHidden && timeLimitHidden.value && timeLimitDisplay) {
            const displayValue = formatDateForDisplay(timeLimitHidden.value, true);
            timeLimitDisplay.value = displayValue;
            console.log('Format existing time limit:', timeLimitHidden.value, '-> Display:', displayValue);
        }

        if (dueDateHidden && dueDateHidden.value && dueDateDisplay) {
            const displayValue = formatDateForDisplay(dueDateHidden.value, false);
            dueDateDisplay.value = displayValue;
            console.log('Format existing due date:', dueDateHidden.value, '-> Display:', displayValue);
        }
    }

    // Add event handlers for format conversion
    if (arrivalDateDisplay && arrivalDateHidden) {
        arrivalDateDisplay.addEventListener('blur', function () {
            const convertedValue = parseDateFromDisplay(this.value, false);
            if (convertedValue && this.value) {
                const reformatted = formatDateForDisplay(convertedValue, false);
                this.value = reformatted;
                arrivalDateHidden.value = convertedValue;
            }
        });
    }

    if (departureDateDisplay && departureDateHidden) {
        departureDateDisplay.addEventListener('blur', function () {
            const convertedValue = parseDateFromDisplay(this.value, false);
            if (convertedValue && this.value) {
                const reformatted = formatDateForDisplay(convertedValue, false);
                this.value = reformatted;
                departureDateHidden.value = convertedValue;
            }
        });
    }

    if (timeLimitDisplay && timeLimitHidden) {
        timeLimitDisplay.addEventListener('blur', function () {
            const convertedValue = parseDateFromDisplay(this.value, true);
            if (convertedValue && this.value) {
                const reformatted = formatDateForDisplay(convertedValue, true);
                this.value = reformatted;
                timeLimitHidden.value = convertedValue;
            }
        });
    }

    if (dueDateDisplay && dueDateHidden) {
        dueDateDisplay.addEventListener('blur', function () {
            const convertedValue = parseDateFromDisplay(this.value, false);
            if (convertedValue && this.value) {
                const reformatted = formatDateForDisplay(convertedValue, false);
                this.value = reformatted;
                dueDateHidden.value = convertedValue;
            }
        });
    }

    // Initialize default dates after a short delay
    setTimeout(setDefaultDatesForEdit, 100);
});
