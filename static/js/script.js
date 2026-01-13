// Cart functionality
document.addEventListener('DOMContentLoaded', function() {
    // Update cart badge
    function updateCartBadge() {
        const cart = JSON.parse(localStorage.getItem('cart') || '{}');
        const badge = document.querySelector('.cart-badge');
        if (badge) {
            const itemCount = Object.keys(cart).length;
            badge.textContent = itemCount;
            badge.style.display = itemCount > 0 ? 'block' : 'none';
        }
    }

    // Add to cart animation
    const addToCartButtons = document.querySelectorAll('.add-to-cart');
    addToCartButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const productId = this.dataset.productId;
            
            // Add animation
            this.classList.add('adding');
            setTimeout(() => {
                this.classList.remove('adding');
                // Submit form
                this.closest('form').submit();
            }, 500);
        });
    });

    // Search functionality
    const searchInput = document.querySelector('.search-input');
    if (searchInput) {
        searchInput.addEventListener('input', debounce(function() {
            // Implement live search if needed
        }, 300));
    }

    // Discount calculation
    const discountInput = document.getElementById('discount');
    if (discountInput) {
        discountInput.addEventListener('input', calculateDiscount);
    }

    updateCartBadge();
});

// Utility functions
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function calculateDiscount() {
    const total = parseFloat(document.getElementById('totalAmount').dataset.total);
    const discount = parseFloat(document.getElementById('discount').value) || 0;
    const discountAmount = total * (discount / 100);
    const finalAmount = total - discountAmount;

    document.getElementById('discountAmount').textContent = `$${discountAmount.toFixed(2)}`;
    document.getElementById('finalAmount').textContent = `$${finalAmount.toFixed(2)}`;
    document.getElementById('finalAmountInput').value = finalAmount.toFixed(2);
}

// Toast notifications
function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    document.body.appendChild(toast);
    new bootstrap.Toast(toast).show();
    setTimeout(() => toast.remove(), 3000);
}