/* ============================================================
   MEDICARE SaaS — Global JavaScript
   Handles: Cart UI, Toast Notifications, Discount Calc, Search
   All existing functionality preserved + enhanced UX
   ============================================================ */
console.log("Global JS Loaded");
document.addEventListener('DOMContentLoaded', function () {

  /* ── 1. Cart Badge ──────────────────────────────────────── */
  function updateCartBadge() {
    const cart = JSON.parse(localStorage.getItem('cart') || '{}');
    const badge = document.querySelector('.cart-badge');
    if (!badge) return;
    const count = Object.keys(cart).length;
    badge.textContent = count;
    badge.style.display = count > 0 ? 'flex' : 'none';
  }

  updateCartBadge();


  /* ── 2. Add to Cart — Button Animation ─────────────────── */
  const addToCartButtons = document.querySelectorAll('.add-to-cart');

  addToCartButtons.forEach(button => {
    button.addEventListener('click', function (e) {
      e.preventDefault();

      const original = this.innerHTML;
      this.classList.add('adding');
      this.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Adding…';
      this.disabled = true;

      setTimeout(() => {
        this.classList.remove('adding');
        this.innerHTML = '<i class="fas fa-check me-2"></i>Added!';

        setTimeout(() => {
          this.innerHTML = original;
          this.disabled = false;
          this.closest('form').submit();
        }, 400);
      }, 500);
    });
  });


  /* ── 3. Live Search (debounced) ─────────────────────────── */
  const searchInput = document.querySelector('.search-input');
  if (searchInput) {
    searchInput.addEventListener('input', debounce(function () {
      // Hook for live search — extend as needed
    }, 300));
  }


  /* ── 4. Discount Calculator ─────────────────────────────── */
  const discountInput = document.getElementById('discount');
  if (discountInput) {
    discountInput.addEventListener('input', calculateDiscount);
    calculateDiscount();
  }


  /* ── 5. Active Nav Link Highlight ──────────────────────── */
  const currentPath = window.location.pathname;
  document.querySelectorAll('.navbar-nav .nav-link').forEach(link => {
    if (link.getAttribute('href') === currentPath) {
      link.classList.add('active');
    }
  });


  /* ── 6. Auto-dismiss Django Alerts (Per Alert Timer) ───── */
/* ── 6. Auto-dismiss Django Alerts (Fix) ───── */
/* Auto-dismiss Django Alerts */

document.querySelectorAll('.django-alert').forEach(alert => {

  let delay = 4000; // default 4 seconds

  if (alert.classList.contains('error') || alert.classList.contains('danger')) {
    delay = 6000; // errors stay longer
  }

  if (alert.classList.contains('info')) {
    delay = 3000; // info shorter
  }

  setTimeout(() => {
    alert.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
    alert.style.opacity = '0';
    alert.style.transform = 'translateY(-10px)';

    setTimeout(() => alert.remove(), 400);
  }, delay);

});
  /* ── 7. Form submit button loading state ───────────────── */
  document.querySelectorAll('form').forEach(form => {
    form.addEventListener('submit', function () {
      const btn = this.querySelector('[type="submit"]');
      if (btn && !btn.dataset.noLoader) {
        btn.disabled = true;
        const orig = btn.innerHTML;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Please wait…';

        setTimeout(() => {
          btn.disabled = false;
          btn.innerHTML = orig;
        }, 5000);
      }
    });
  });

});


/* ── Alert Timer Function ─────────────────────────────────── */
function startAlertTimer(alert, delay) {
  return setTimeout(() => {
    alert.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
    alert.style.opacity = '0';
    alert.style.transform = 'translateY(-8px)';
    setTimeout(() => alert.remove(), 400);
  }, delay);
}


/* ── Utility: Debounce ───────────────────────────────────── */
function debounce(func, wait) {
  let timeout;
  return function (...args) {
    clearTimeout(timeout);
    timeout = setTimeout(() => func.apply(this, args), wait);
  };
}


/* ── Discount Calculation ───────────────────────────────── */
function calculateDiscount() {
  const totalEl    = document.getElementById('totalAmount');
  const discountEl = document.getElementById('discount');
  const discAmtEl  = document.getElementById('discountAmount');
  const finalAmtEl = document.getElementById('finalAmount');
  const finalInput = document.getElementById('finalAmountInput');

  if (!totalEl || !discountEl) return;

  const total        = parseFloat(totalEl.dataset.total) || 0;
  const discountPct  = Math.min(Math.max(parseFloat(discountEl.value) || 0, 0), 100);
  const discountAmt  = total * (discountPct / 100);
  const finalAmount  = total - discountAmt;

  if (discAmtEl)  discAmtEl.textContent  = `₹${discountAmt.toFixed(2)}`;
  if (finalAmtEl) finalAmtEl.textContent = `₹${finalAmount.toFixed(2)}`;
  if (finalInput) finalInput.value       = finalAmount.toFixed(2);
}


/* ── Toast Notifications (unchanged) ───────────────────── */
function showToast(message, type = 'success') {

  const config = {
    success: { icon: 'fa-check-circle', bg: '#f0fdf4', border: '#bbf7d0', color: '#15803d' },
    danger:  { icon: 'fa-exclamation-circle', bg: '#fef2f2', border: '#fecaca', color: '#dc2626' },
    warning: { icon: 'fa-exclamation-triangle', bg: '#fffbeb', border: '#fde68a', color: '#d97706' },
    info:    { icon: 'fa-info-circle', bg: '#f0f9ff', border: '#bae6fd', color: '#0284c7' },
  };

  const c = config[type] || config.info;

  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    Object.assign(container.style, {
      position: 'fixed',
      bottom: '1.5rem',
      right: '1.5rem',
      zIndex: '9999',
      display: 'flex',
      flexDirection: 'column',
      gap: '0.6rem',
    });
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  Object.assign(toast.style, {
    display: 'flex',
    alignItems: 'center',
    gap: '0.75rem',
    padding: '0.85rem 1.1rem',
    background: c.bg,
    border: `1px solid ${c.border}`,
    borderRadius: '12px',
    color: c.color,
    fontFamily: "'DM Sans', sans-serif",
    fontSize: '0.875rem',
    fontWeight: '500',
    boxShadow: '0 4px 20px rgba(0,0,0,0.1)',
    minWidth: '260px',
    maxWidth: '360px',
    opacity: '0',
    transform: 'translateY(8px)',
    transition: 'opacity 0.25s ease, transform 0.25s ease',
  });

  toast.innerHTML = `
    <i class="fas ${c.icon}" style="font-size:1rem; flex-shrink:0;"></i>
    <span style="flex:1;">${message}</span>
    <button onclick="this.parentElement.remove()" style="background:none;border:none;cursor:pointer;color:${c.color};padding:0;font-size:1rem;line-height:1;opacity:0.7;">
      <i class="fas fa-times"></i>
    </button>
  `;

  container.appendChild(toast);

  requestAnimationFrame(() => {
    toast.style.opacity = '1';
    toast.style.transform = 'translateY(0)';
  });

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(8px)';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}