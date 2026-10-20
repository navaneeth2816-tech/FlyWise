/**
 * FlyWise AI - Unified API Client & State Management
 */
// Automatically detect environment: local dev uses local Flask backend, production uses deployed Render backend
const isLocal = typeof window !== 'undefined' && 
  (window.location.hostname === 'localhost' || 
   window.location.hostname === '127.0.0.1' || 
   window.location.hostname === '');

const API_BASE = isLocal 
  ? '/api/v1' 
  : 'https://flywise-0equ.onrender.com/api/v1';

const api = {
  getToken() {
    return localStorage.getItem('flywise_token') || '';
  },

  setToken(token) {
    if (token) localStorage.setItem('flywise_token', token);
    else localStorage.removeItem('flywise_token');
  },

  getUser() {
    const raw = localStorage.getItem('flywise_user');
    try {
      return raw ? JSON.parse(raw) : null;
    } catch (e) {
      return null;
    }
  },

  setUser(user) {
    if (user) localStorage.setItem('flywise_user', JSON.stringify(user));
    else localStorage.removeItem('flywise_user');
  },

  async request(endpoint, options = {}) {
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers
    };

    const token = this.getToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const config = {
      ...options,
      headers
    };

    try {
      const cleanEndpoint = endpoint.startsWith('/api/v1') 
        ? endpoint.replace('/api/v1', '') 
        : endpoint;
      const response = await fetch(`${API_BASE}${cleanEndpoint}`, config);
      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(data.message || `Request failed with status ${response.status}`);
      }
      return data;
    } catch (error) {
      console.error(`API Error [${endpoint}]:`, error);
      throw error;
    }
  },

  get(endpoint, params = {}) {
    const query = new URLSearchParams(params).toString();
    const url = query ? `${endpoint}?${query}` : endpoint;
    return this.request(url, { method: 'GET' });
  },

  post(endpoint, body = {}) {
    return this.request(endpoint, {
      method: 'POST',
      body: JSON.stringify(body)
    });
  },

  patch(endpoint, body = {}) {
    return this.request(endpoint, {
      method: 'PATCH',
      body: JSON.stringify(body)
    });
  },

  delete(endpoint) {
    return this.request(endpoint, { method: 'DELETE' });
  }
};

function showToast(message, type = 'info') {
  let container = document.querySelector('.toast-container');
  if (!container) {
    container = document.createElement('div');
    container.className = 'toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `
    <i class="fa-solid ${type === 'success' ? 'fa-circle-check' : type === 'danger' ? 'fa-triangle-exclamation' : 'fa-info-circle'}"></i>
    <span>${message}</span>
  `;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}
