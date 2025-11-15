// PRODUCTS & CALCULATION - CLEAN JAVASCRIPT FOR EDIT FORM

document.addEventListener('DOMContentLoaded', function () {
    console.log('🚀 Initializing Products & Calculation for Edit Form...');

    let productRowCount = 1;

    // Update grand total function
    function updateGrandTotal() {
        let total = 0;
        document.querySelectorAll('.product-amount').forEach(input => {
            total += parseFloat(input.value) || 0;
        });

        console.log('Grand total calculated:', total);

        const formattedTotal = total.toLocaleString('en-US', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });

        const grandTotalSpan = document.getElementById('grand-total');
        if (grandTotalSpan) {
            grandTotalSpan.textContent = formattedTotal;
        }

        const totalAmountInput = document.getElementById('total_amount');
        if (totalAmountInput) {
            totalAmountInput.value = total.toFixed(2);
        }
    }

    // Update row numbers
    function updateRowNumbers() {
        const rows = document.querySelectorAll('.product-row');
        rows.forEach((row, index) => {
            const numberCell = row.querySelector('.row-number');
            if (numberCell) {
                numberCell.textContent = index + 1;
            }
        });
    }

    // Update field names
    function updateFieldNames() {
        const rows = document.querySelectorAll('.product-row');
        rows.forEach((row, index) => {
            const nameInput = row.querySelector('.product-name');
            const quantityInput = row.querySelector('.product-quantity');
            const priceInput = row.querySelector('.product-price');
            const amountInput = row.querySelector('.product-amount');

            if (nameInput) nameInput.name = `products[${index}][name]`;
            if (quantityInput) quantityInput.name = `products[${index}][quantity]`;
            if (priceInput) priceInput.name = `products[${index}][price]`;
            if (amountInput) amountInput.name = `products[${index}][amount]`;
        });
    }

    // Calculate amount for a row
    function calculateAmount(row) {
        const quantityInput = row.querySelector('.product-quantity');
        const priceInput = row.querySelector('.product-price');
        const amountInput = row.querySelector('.product-amount');

        const quantity = parseFloat(quantityInput.value) || 0;
        const price = parseFloat(priceInput.value) || 0;
        const amount = quantity * price;

        amountInput.value = amount.toFixed(2);
        updateGrandTotal();
    }

    // Bind events to a row
    function bindRowEvents(row) {
        const quantityInput = row.querySelector('.product-quantity');
        const priceInput = row.querySelector('.product-price');
        const moveUpBtn = row.querySelector('.move-up');
        const moveDownBtn = row.querySelector('.move-down');
        const deleteBtn = row.querySelector('.delete-row');

        if (quantityInput) {
            quantityInput.addEventListener('input', () => calculateAmount(row));
        }
        if (priceInput) {
            priceInput.addEventListener('input', () => calculateAmount(row));
        }
        if (deleteBtn) {
            deleteBtn.addEventListener('click', () => deleteRow(row));
        }
        if (moveUpBtn) {
            moveUpBtn.addEventListener('click', () => moveRowUp(row));
        }
        if (moveDownBtn) {
            moveDownBtn.addEventListener('click', () => moveRowDown(row));
        }
    }

    // Delete row function
    function deleteRow(row) {
        const nameInput = row.querySelector('.product-name');
        const hasData = nameInput && nameInput.value.trim() !== '';

        if (hasData) {
            if (!confirm('Are you sure you want to delete this product?')) {
                return;
            }
        }

        row.remove();
        updateRowNumbers();
        updateFieldNames();
        updateGrandTotal();
        productRowCount = document.querySelectorAll('.product-row').length;
    }

    // Move row up
    function moveRowUp(row) {
        const prevRow = row.previousElementSibling;
        if (prevRow && prevRow.classList.contains('product-row')) {
            row.parentNode.insertBefore(row, prevRow);
            updateRowNumbers();
            updateFieldNames();
        }
    }

    // Move row down
    function moveRowDown(row) {
        const nextRow = row.nextElementSibling;
        if (nextRow && nextRow.classList.contains('product-row')) {
            row.parentNode.insertBefore(nextRow, row);
            updateRowNumbers();
            updateFieldNames();
        }
    }

    // Add new row
    function addProductRow() {
        const tbody = document.getElementById('products-tbody');
        if (!tbody) return;

        const newRow = document.createElement('tr');
        newRow.className = 'product-row';
        newRow.innerHTML = `
            <td class="row-number">${productRowCount + 1}</td>
            <td><input type="text" class="form-control product-name" name="products[${productRowCount}][name]" placeholder="Enter product name"></td>
            <td><input type="number" class="form-control product-quantity" name="products[${productRowCount}][quantity]" min="1" value="1" placeholder="1"></td>
            <td><input type="number" class="form-control product-price" name="products[${productRowCount}][price]" step="0.01" placeholder="0.00"></td>
            <td><input type="number" class="form-control product-amount" name="products[${productRowCount}][amount]" step="0.01" readonly></td>
            <td class="text-center">
                <div class="btn-group-vertical" role="group">
                    <button type="button" class="btn btn-outline-primary btn-sm move-up" title="Move Up"><i class="fas fa-chevron-up"></i></button>
                    <button type="button" class="btn btn-outline-primary btn-sm move-down" title="Move Down"><i class="fas fa-chevron-down"></i></button>
                </div>
            </td>
            <td class="text-center">
                <button type="button" class="btn btn-outline-danger btn-sm delete-row" title="Delete Row"><i class="fas fa-trash"></i></button>
            </td>
        `;

        tbody.appendChild(newRow);
        bindRowEvents(newRow);
        productRowCount++;
        updateRowNumbers();
        updateFieldNames();
    }

    // Initialize existing rows
    const existingRows = document.querySelectorAll('.product-row');
    existingRows.forEach(bindRowEvents);
    productRowCount = existingRows.length;

    // Add row button
    const addRowBtn = document.getElementById('add-product-row');
    if (addRowBtn) {
        addRowBtn.addEventListener('click', addProductRow);
    }

    // Initial calculation
    updateGrandTotal();

    // Load existing products data - SIMPLIFIED VERSION
    console.log('🔄 Loading existing products data...');

    // Make functions globally accessible
    window.updateGrandTotal = updateGrandTotal;
    window.updateRowNumbers = updateRowNumbers;
    window.updateFieldNames = updateFieldNames;
    window.bindRowEvents = bindRowEvents;
    window.deleteRow = deleteRow;

    // Load products data if available
    {% if booking.get_products() %}
    try {
        const productsData = {{ booking.get_products() | tojson | safe
    }};
console.log('📦 Products data received:', productsData);

if (productsData && productsData.length > 0) {
    const tbody = document.getElementById('products-tbody');
    if (tbody) {
        tbody.innerHTML = ''; // Clear existing rows

        productsData.forEach((product, index) => {
            const row = tbody.insertRow();
            row.className = 'product-row';
            row.innerHTML = `
                        <td class="row-number">${index + 1}</td>
                        <td><input type="text" class="form-control product-name" name="products[${index}][name]" value="${product.name || ''}" placeholder="Enter product name"></td>
                        <td><input type="number" class="form-control product-quantity" name="products[${index}][quantity]" value="${product.quantity || 1}" min="1" placeholder="1"></td>
                        <td><input type="number" class="form-control product-price" name="products[${index}][price]" value="${product.price || ''}" step="0.01" placeholder="0.00"></td>
                        <td><input type="number" class="form-control product-amount" name="products[${index}][amount]" value="${product.amount || ''}" step="0.01" readonly></td>
                        <td class="text-center">
                            <div class="btn-group-vertical" role="group">
                                <button type="button" class="btn btn-outline-primary btn-sm move-up" title="Move Up"><i class="fas fa-chevron-up"></i></button>
                                <button type="button" class="btn btn-outline-primary btn-sm move-down" title="Move Down"><i class="fas fa-chevron-down"></i></button>
                            </div>
                        </td>
                        <td class="text-center">
                            <button type="button" class="btn btn-outline-danger btn-sm delete-row" title="Delete Row"><i class="fas fa-trash"></i></button>
                        </td>
                    `;
            bindRowEvents(row);
            console.log(`✅ Loaded product: ${product.name} - ${product.quantity} x ${product.price} = ${product.amount}`);
        });

        productRowCount = productsData.length;
        updateRowNumbers();
        setTimeout(updateGrandTotal, 100);
        console.log(`🎯 Successfully loaded ${productsData.length} products!`);
    }
}
    } catch (error) {
    console.error('❌ Error loading products:', error);
}
{% else %}
console.log('ℹ️ No products data available for this booking');
{% endif %}

console.log('✅ Products & Calculation system initialized successfully!');
});
