// Simple Date Picker - No CORS Issues
class SimpleDatePicker {
    constructor(input, options = {}) {
        this.input = input;
        this.options = {
            format: 'DD/MM/YYYY',
            enableTime: false,
            ...options
        };
        this.isOpen = false;
        this.selectedDate = null;
        this.currentMonth = new Date();
        this.currentMonth.setDate(1);

        this.init();
    }

    init() {
        this.input.addEventListener('click', () => this.open());
        this.input.addEventListener('focus', () => this.open());
        this.input.readonly = true;
        document.addEventListener('click', (e) => this.handleOutsideClick(e));
    }

    open() {
        console.log('SimpleDatePicker.open() called for:', this.input.id);

        // Close any other open pickers first
        document.querySelectorAll('input[data-picker-open="true"]').forEach(input => {
            if (input._simpleDatePicker && input !== this.input) {
                input._simpleDatePicker.close();
            }
        });

        if (this.isOpen && this.picker) {
            console.log('Picker already open, returning');
            return;
        }

        // Clean up any orphaned picker elements
        document.querySelectorAll('.simple-datepicker').forEach(existingPicker => {
            existingPicker.remove();
        });

        this.isOpen = true;
        this.input.setAttribute('data-picker-open', 'true');

        this.createPicker();
        this.positionPicker();

        console.log('Picker opened successfully');
    }

    close() {
        console.log('SimpleDatePicker.close() called');

        if (!this.isOpen) {
            return;
        }

        this.isOpen = false;
        this.input.removeAttribute('data-picker-open');

        if (this.picker && this.picker.parentNode) {
            this.picker.parentNode.removeChild(this.picker);
        }
        this.picker = null;

        console.log('Picker closed successfully');
    }

    createPicker() {
        this.picker = document.createElement('div');
        this.picker.className = 'simple-datepicker';
        this.picker.innerHTML = this.generateHTML();
        document.body.appendChild(this.picker);
        this.bindEvents();
        this.updateCalendar();
    }

    generateHTML() {
        const currentYear = this.currentMonth.getFullYear();
        const currentMonthIndex = this.currentMonth.getMonth();
        const monthNames = [
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ];

        return `
            <div style="position: absolute; z-index: 9999; background: white; border: 1px solid #ddd; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; font-size: 14px; width: 280px; max-height: 350px; overflow: hidden;">
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; background: #f8f9fa; border-bottom: 1px solid #e9ecef;">
                    <button type="button" class="prev-month" style="background: none; border: none; cursor: pointer; font-size: 18px; color: #6c757d; padding: 4px 8px; border-radius: 4px;">‹</button>
                    <span class="month-year-display" style="font-weight: 600; color: #495057;">${monthNames[currentMonthIndex]} ${currentYear}</span>
                    <button type="button" class="next-month" style="background: none; border: none; cursor: pointer; font-size: 18px; color: #6c757d; padding: 4px 8px; border-radius: 4px;">›</button>
                </div>
                <div class="calendar-grid" style="background: white;">
                    ${this.generateDays()}
                </div>
            </div>
        `;
    }

    generateDays() {
        const weekdays = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'];
        const currentYear = this.currentMonth.getFullYear();
        const currentMonthIndex = this.currentMonth.getMonth();

        const firstDay = new Date(currentYear, currentMonthIndex, 1);
        const lastDay = new Date(currentYear, currentMonthIndex + 1, 0);
        const daysInMonth = lastDay.getDate();
        const startDay = firstDay.getDay();

        let html = `
            <div style="display: grid; grid-template-columns: repeat(7, 1fr); gap: 1px; background: #f8f9fa; padding: 8px; font-size: 12px; font-weight: 600; color: #6c757d;">
                ${weekdays.map(day => `<div style="text-align: center; padding: 4px;">${day}</div>`).join('')}
            </div>
            <div style="display: grid; grid-template-columns: repeat(7, 1fr); gap: 1px; padding: 8px; background: white; overflow-y: auto; max-height: 250px;">
        `;

        // Empty cells for days before the first day of the month
        for (let i = 0; i < startDay; i++) {
            html += '<div style="padding: 8px;"></div>';
        }

        // Days of the month
        for (let day = 1; day <= daysInMonth; day++) {
            const date = new Date(currentYear, currentMonthIndex, day);
            const isToday = this.isToday(date);
            const isSelected = this.isSelected(date);

            let dayStyle = 'padding: 8px; text-align: center; cursor: pointer; border-radius: 4px; transition: background-color 0.2s;';

            if (isToday) {
                dayStyle += ' background-color: #e3f2fd; color: #1976d2; font-weight: 600;';
            } else if (isSelected) {
                dayStyle += ' background-color: #2196f3; color: white; font-weight: 600;';
            } else {
                dayStyle += ' color: #495057;';
            }

            html += `<div class="day-cell" data-date="${date.toISOString()}" style="${dayStyle}" onmouseover="this.style.backgroundColor='#f5f5f5'" onmouseout="this.style.backgroundColor='${isSelected ? '#2196f3' : (isToday ? '#e3f2fd' : 'transparent')}'">${day}</div>`;
        }

        html += '</div>';
        return html;
    }

    bindEvents() {
        // Month navigation
        this.picker.querySelector('.prev-month').addEventListener('click', () => {
            this.currentMonth.setMonth(this.currentMonth.getMonth() - 1);
            this.updateCalendar();
        });

        this.picker.querySelector('.next-month').addEventListener('click', () => {
            this.currentMonth.setMonth(this.currentMonth.getMonth() + 1);
            this.updateCalendar();
        });

        // Day selection
        this.picker.addEventListener('click', (e) => {
            if (e.target.classList.contains('day-cell')) {
                const selectedDate = new Date(e.target.dataset.date);
                this.selectedDate = selectedDate;
                this.updateInput();
                this.close();
            }
        });
    }

    updateCalendar() {
        const calendarGrid = this.picker.querySelector('.calendar-grid');
        calendarGrid.innerHTML = this.generateDays();

        // Update month/year display
        const currentYear = this.currentMonth.getFullYear();
        const currentMonthIndex = this.currentMonth.getMonth();
        const monthNames = [
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ];
        const monthYearDisplay = this.picker.querySelector('.month-year-display');
        if (monthYearDisplay) {
            monthYearDisplay.textContent = `${monthNames[currentMonthIndex]} ${currentYear}`;
        }

        // Re-bind day selection events
        this.picker.addEventListener('click', (e) => {
            if (e.target.classList.contains('day-cell')) {
                const selectedDate = new Date(e.target.dataset.date);
                this.selectedDate = selectedDate;
                this.updateInput();
                this.close();
            }
        });
    }

    updateInput() {
        if (this.selectedDate) {
            const day = String(this.selectedDate.getDate()).padStart(2, '0');
            const month = String(this.selectedDate.getMonth() + 1).padStart(2, '0');
            const year = this.selectedDate.getFullYear();

            // Check if this is a datetime input (time_limit)
            if (this.input.classList.contains('datetime-input')) {
                // Add default time if not already present
                const currentValue = this.input.value;
                let timepart = ' 12:00';
                if (currentValue && currentValue.includes(' ')) {
                    timepart = ' ' + currentValue.split(' ')[1];
                }
                this.input.value = `${day}/${month}/${year}${timepart}`;
            } else {
                this.input.value = `${day}/${month}/${year}`;
            }

            // Trigger change event
            const event = new Event('change', { bubbles: true });
            this.input.dispatchEvent(event);
        }
    }

    positionPicker() {
        if (!this.picker) return;

        const inputRect = this.input.getBoundingClientRect();
        const pickerRect = this.picker.getBoundingClientRect();
        const viewportHeight = window.innerHeight;
        const viewportWidth = window.innerWidth;
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        const scrollLeft = window.pageXOffset || document.documentElement.scrollLeft;

        // Calculate space above and below the input
        const spaceBelow = viewportHeight - (inputRect.bottom - window.pageYOffset);
        const spaceAbove = inputRect.top - window.pageYOffset;
        const pickerHeight = Math.min(350, pickerRect.height);

        let top, left;

        // Determine vertical position
        if (spaceBelow >= pickerHeight || spaceBelow >= spaceAbove) {
            // Position below the input
            top = inputRect.bottom + scrollTop + 2;
        } else {
            // Position above the input
            top = inputRect.top + scrollTop - pickerHeight - 2;
        }

        // Determine horizontal position
        left = inputRect.left + scrollLeft;

        // Ensure picker doesn't go off-screen horizontally
        if (left + 280 > viewportWidth) {
            left = viewportWidth - 280 - 10;
        }
        if (left < 10) {
            left = 10;
        }

        // Ensure picker doesn't go off-screen vertically
        if (top < scrollTop + 10) {
            top = scrollTop + 10;
        }
        if (top + pickerHeight > scrollTop + viewportHeight - 10) {
            top = scrollTop + viewportHeight - pickerHeight - 10;
        }

        this.picker.style.top = `${top}px`;
        this.picker.style.left = `${left}px`;
        this.picker.style.position = 'absolute';
    }

    isToday(date) {
        const today = new Date();
        return date.toDateString() === today.toDateString();
    }

    isSelected(date) {
        if (!this.selectedDate) return false;
        return date.toDateString() === this.selectedDate.toDateString();
    }

    handleOutsideClick(e) {
        if (this.isOpen && this.picker && !this.picker.contains(e.target) && !this.input.contains(e.target)) {
            this.close();
        }
    }
}

// Global initialization function
function initSimpleDatePickers() {
    console.log('Initializing SimpleDatePickers...');

    const dateInputs = document.querySelectorAll('input[data-date-picker]');
    console.log('Found date inputs:', dateInputs.length);

    dateInputs.forEach(input => {
        if (!input._simpleDatePicker) {
            console.log('Initializing picker for:', input.id);
            input._simpleDatePicker = new SimpleDatePicker(input);
        }
    });
}

// Auto-initialize on DOM ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initSimpleDatePickers);
} else {
    initSimpleDatePickers();
}