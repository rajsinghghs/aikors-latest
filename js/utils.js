/**
 * utils.js — AIkors shared utilities
 * Icons, Auth, API, Toast, Navbar, Motion helpers, formatting, loading states.
 * Public names (Icons, Auth, API, Toast, setupNavbar, logout, formatPrice,
 * formatDate, setLoading, productSkeleton, discountPercent, togglePassword)
 * are unchanged so existing pages and auth.js keep working.
 */

// ─── API Base ────────────────────────────────────────────────────────────────
const API_BASE = '/api';

// ─── Icons (Lucide-style line icons, 2px stroke) ─────────────────────────────
const _svg = (inner, size = 20, sw = 2) =>
  `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="${sw}" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">${inner}</svg>`;

const Icons = {
  check: _svg('<polyline points="20 6 9 17 4 12"/>'),
  success: _svg('<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>'),
  error: _svg('<circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>'),
  info: _svg('<circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>'),
  loader: `<svg class="spinner" xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg>`,
  eye: _svg('<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>', 18),
  eyeOff: _svg('<path d="M9.88 9.88a3 3 0 1 0 4.24 4.24"/><path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68"/><path d="M6.61 6.61A13.53 13.53 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61"/><line x1="2" y1="2" x2="22" y2="22"/>', 18),
  logout: _svg('<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>', 26 , 2.3),
  lock: _svg('<rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>', 24),
  mail: _svg('<rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 7-10 5L2 7"/>', 22),
  arrowLeft: _svg('<line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/>', 16),
  home: _svg('<path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>', 18),
  compass: _svg('<circle cx="12" cy="12" r="10"/><polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"/>', 18)
};

// ─── Auth token management ───────────────────────────────────────────────────
const Auth = {
  getToken: () => localStorage.getItem('cv_token'),
  getUser: () => {
    const raw = localStorage.getItem('cv_user');
    try { return raw ? JSON.parse(raw) : null; } catch { return null; }
  },
  setSession: (token, user) => {
    localStorage.setItem('cv_token', token);
    localStorage.setItem('cv_user', JSON.stringify(user));
  },
  clear: () => {
    localStorage.removeItem('cv_token');
    localStorage.removeItem('cv_user');
  },
  isLoggedIn: () => !!localStorage.getItem('cv_token'),
  isAdmin: () => {
    const user = Auth.getUser();
    return user && user.role === 'admin';
  }
};

// ─── 🚀 GOOGLE AUTH AUTO-HEALING LOGIC ───────────────────────────────────────
// Yeh automatically URL se token uthayega, user ki detail fetch karega aur save karega
(async function handleGoogleRedirect() {
  const urlParams = new URLSearchParams(window.location.search);
  const urlToken = urlParams.get('token');
  
  if (urlToken) {
    // URL se token hide kar do
    window.history.replaceState({}, document.title, window.location.pathname);
    
    // Save token using correct key
    localStorage.setItem('cv_token', urlToken);
    
    try {
      // Fetch user data from backend because Google redirect only gives token
      const res = await fetch(`${API_BASE}/auth/me`, {
        headers: { 'Authorization': `Bearer ${urlToken}` }
      });
      if (res.ok) {
        const user = await res.json();
        localStorage.setItem('cv_user', JSON.stringify(user));
      }
    } catch (err) {
      console.error("Failed to fetch user data for Google Auth", err);
    }
    
    // Reload page to apply changes properly
    window.location.reload();
  }
})();
// ─────────────────────────────────────────────────────────────────────────────

// ─── API client (behavior unchanged) ─────────────────────────────────────────
const API = {
  async request(path, options = {}) {
    const token = Auth.getToken();
    const headers = {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
      ...(options.headers || {})
    };

    // Prevent double /api/api in URLs
    const finalUrl = path.startsWith('/api') ? path : `${API_BASE}${path}`;
    const res = await fetch(finalUrl, { ...options, headers });

    // Only redirect on expired token; a failed login must not redirect.
    if (res.status === 401 && !path.includes('/auth/login')) {
      Auth.clear(); window.location.href = '/login'; return;
    }

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const message = data.detail || `Request failed: ${res.status}`;
      throw new Error(typeof message === 'string' ? message : JSON.stringify(message));
    }
    return data;
  },
  get: (path) => API.request(path),
  post: (path, body) => API.request(path, { method: 'POST', body: JSON.stringify(body) }),
  put: (path, body) => API.request(path, { method: 'PUT', body: JSON.stringify(body) }),
  patch: (path, body) => API.request(path, { method: 'PATCH', body: JSON.stringify(body) }),
  delete: (path) => API.request(path, { method: 'DELETE' }),
  upload: (path, formData) => {
    const token = Auth.getToken();
    const finalUrl = path.startsWith('/api') ? path : `${API_BASE}${path}`;
    return fetch(finalUrl, {
      method: 'POST',
      headers: token ? { 'Authorization': `Bearer ${token}` } : {},
      body: formData
    }).then(async r => {
      if (r.status === 401 && !path.includes('/auth/login')) {
        Auth.clear(); window.location.href = '/login'; return;
      }
      const d = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(d.detail || 'Upload failed');
      return d;
    });
  }
};

// ─── Toast ───────────────────────────────────────────────────────────────────
const Toast = {
  container: null,
  init() {
    this.container = document.getElementById('toast-container');
    if (!this.container) {
      this.container = document.createElement('div');
      this.container.id = 'toast-container';
      document.body.appendChild(this.container);
    }
    this.container.setAttribute('role', 'region');
    this.container.setAttribute('aria-label', 'Notifications');
  },
  show(message, type = 'info', duration = 4000) {
    if (!this.container) this.init();

    const kind = ['success', 'error', 'info'].includes(type) ? type : 'info';
    const iconSvg = kind === 'success' ? Icons.success : (Icons[kind] || Icons.info);

    const toast = document.createElement('div');
    toast.className = `toast toast-${kind}`;
    toast.setAttribute('role', kind === 'error' ? 'alert' : 'status');
    toast.innerHTML = `
      <div class="toast-icon">${iconSvg}</div>
      <div class="toast-content">${message}</div>
    `;
    this.container.appendChild(toast);

    let timer;
    const dismiss = () => {
      clearTimeout(timer);
      if (toast.classList.contains('hiding')) return;
      toast.classList.add('hiding');
      const done = () => toast.remove();
      toast.addEventListener('animationend', done, { once: true });
      setTimeout(done, 400); // safety net (e.g. reduced motion)
    };
    timer = setTimeout(dismiss, duration);
    toast.addEventListener('click', dismiss);
  },
  success: (msg) => Toast.show(msg, 'success'),
  error: (msg) => Toast.show(msg, 'error'),
  info: (msg) => Toast.show(msg, 'info')
};

// ─── Motion helpers ──────────────────────────────────────────────────────────
const Motion = {
  reduced: () => window.matchMedia('(prefers-reduced-motion: reduce)').matches,
  reveal(selector = '.reveal') {
    const els = document.querySelectorAll(selector);
    if (!els.length) return;
    if (this.reduced() || !('IntersectionObserver' in window)) {
      els.forEach(el => el.classList.add('in'));
      return;
    }
    const io = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        const el = entry.target;
        const delay = el.dataset.revealDelay;
        if (delay) el.style.setProperty('--reveal-delay', `${parseInt(delay, 10) || 0}ms`);
        el.classList.add('in');
        io.unobserve(el);
      });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 });
    els.forEach(el => io.observe(el));
  }
};

// ─── Password visibility toggle ──────────────────────────────────────────────
function togglePassword(id, btn) {
  const input = document.getElementById(id);
  if (!input || !btn) return;
  const show = input.type === 'password';
  input.type = show ? 'text' : 'password';
  btn.innerHTML = show ? Icons.eyeOff : Icons.eye;
  btn.setAttribute('aria-pressed', String(show));
  btn.setAttribute('aria-label', show ? 'Hide password' : 'Show password');
}

// ─── Navbar ──────────────────────────────────────────────────────────────────
function _escapeText(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function setupNavbar() {
  const navbar = document.querySelector('.navbar');
  if (navbar) {
    let ticking = false;
    const update = () => {
      navbar.classList.toggle('scrolled', window.scrollY > 10);
      ticking = false;
    };
    window.addEventListener('scroll', () => {
      if (!ticking) { ticking = true; requestAnimationFrame(update); }
    }, { passive: true });
    update();
  }

  const navActions = document.getElementById('nav-actions');
  if (!navActions) return;

  const user = Auth.getUser();
  if (Auth.isLoggedIn() && user) {
    const firstName = _escapeText((user.name || '').split(' ')[0]);
    navActions.innerHTML = `
      <div class="nav-user">
        <span class="nav-greeting">Hey, ${firstName}</span>
        ${Auth.isAdmin() ? `<a href="/admin" class="btn-ghost btn-sm">Admin</a>` : ''}
        <a href="/dashboard" class="btn-primary btn-sm">Dashboard</a>
       <button onclick="logout()" class="btn-ghost btn-icon nav-logout" title="Log out" aria-label="Log out" >${Icons.logout}</button>
      </div>
    `;
  } else {
    navActions.innerHTML = `
      <button onclick="window.location.href='/login'" class="btn-ghost btn-sm">Log in</button>
      <button onclick="window.location.href='/signup'" class="btn-primary btn-sm">Sign up</button>
    `;
  }
}

function logout() {
  Auth.clear();
  Toast.success('Logged out successfully');
  setTimeout(() => window.location.href = '/', 800);
}

// ─── Formatting ──────────────────────────────────────────────────────────────
function renderStars(rating, count) {
  const total = Number(count) || 0;
  if (!total || rating == null) return '';
  const rounded = Math.max(1, Math.min(5, Math.round(Number(rating))));
  const stars = '★★★★★'.slice(0, rounded) + '☆☆☆☆☆'.slice(0, 5 - rounded);
  const label = `${Number(rating).toFixed(1)} out of 5 from ${total} review${total === 1 ? '' : 's'}`;
  return `<span class="star-line" role="img" aria-label="${label}"><b aria-hidden="true">${stars}</b> ${Number(rating).toFixed(1)} (${total})</span>`;
}

function formatPrice(amount) {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency', currency: 'INR',
    minimumFractionDigits: 0, maximumFractionDigits: 0
  }).format(amount);
}

function formatDate(dateStr) {
  return new Date(dateStr).toLocaleDateString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric'
  });
}

// ─── Button loading state ────────────────────────────────────────────────────
function setLoading(btn, loading, text = 'Processing...') {
  if (!btn) return;
  if (loading) {
    btn.disabled = true;
    btn.setAttribute('aria-busy', 'true');
    if (btn.dataset.originalHtml === undefined) btn.dataset.originalHtml = btn.innerHTML;
    btn.innerHTML = `${Icons.loader}<span>${text}</span>`;
  } else {
    btn.disabled = false;
    btn.removeAttribute('aria-busy');
    if (btn.dataset.originalHtml !== undefined) {
      btn.innerHTML = btn.dataset.originalHtml;
      delete btn.dataset.originalHtml;
    } else {
      btn.textContent = text;
    }
  }
}

// ─── Skeleton ────────────────────────────────────────────────────────────────
function productSkeleton() {
  return `
    <div class="product-card" style="pointer-events:none;" aria-hidden="true">
      <div class="skeleton" style="width:100%; aspect-ratio: 16/9; border-radius: var(--radius-lg) var(--radius-lg) 0 0;"></div>
      <div class="product-card-body">
        <div class="skeleton" style="height:18px; width:70%; margin-bottom:8px;"></div>
        <div class="skeleton" style="height:14px; width:100%; margin-bottom:4px;"></div>
        <div class="skeleton" style="height:14px; width:85%; margin-bottom:20px;"></div>
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <div class="skeleton" style="height:24px; width:60px;"></div>
          <div class="skeleton" style="height:36px; width:90px; border-radius: var(--radius-md);"></div>
        </div>
      </div>
    </div>
  `;
}

// ─── Discount ────────────────────────────────────────────────────────────────
function discountPercent(price, original) {
  if (!original || original <= price) return null;
  return Math.round(((original - price) / original) * 100);
}

// ─── Init ────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  Toast.init();
  setupNavbar();
  Motion.reveal();
});