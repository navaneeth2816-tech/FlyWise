/**
 * FlyWise AI - Main Application Controller & View Routing
 */

document.addEventListener('DOMContentLoaded', () => {
  initApp();
});

function initApp() {
  updateAuthUI();
  setupEventListeners();

  // Set default search date to upcoming date (Oct 23, 2026)
  const dateInput = document.getElementById('search-date');
  if (dateInput) {
    dateInput.value = '2026-10-23';
  }

  // Pre-fill default route: Tirupati to Delhi (PRD scenario)
  const orig = document.getElementById('search-origin');
  const dest = document.getElementById('search-destination');
  if (orig && !orig.value) orig.value = 'TIR';
  if (dest && !dest.value) dest.value = 'DEL';
}

function setupEventListeners() {
  // Flight search form
  const searchForm = document.getElementById('flight-search-form');
  if (searchForm) {
    searchForm.addEventListener('submit', performFlightSearch);
  }

  // Assistant chat input
  const chatForm = document.getElementById('ai-chat-form');
  if (chatForm) {
    chatForm.addEventListener('submit', handleAssistantSubmit);
  }

  // Auth forms
  const loginForm = document.getElementById('login-form');
  if (loginForm) {
    loginForm.addEventListener('submit', handleLogin);
  }

  const registerForm = document.getElementById('register-form');
  if (registerForm) {
    registerForm.addEventListener('submit', handleRegister);
  }

  // Live password validation listeners
  const regPwd = document.getElementById('register-password');
  const regConfirmPwd = document.getElementById('register-confirm-password');
  if (regPwd) {
    regPwd.addEventListener('input', updatePasswordLiveValidation);
  }
  if (regConfirmPwd) {
    regConfirmPwd.addEventListener('input', updatePasswordLiveValidation);
  }
}

function switchView(viewId) {
  document.querySelectorAll('.app-view').forEach(v => {
    v.style.display = 'none';
  });

  const target = document.getElementById(viewId);
  if (target) {
    target.style.display = 'block';
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  // Update navigation link highlights
  document.querySelectorAll('.nav-link').forEach(link => {
    link.classList.remove('active');
    if (link.dataset.view === viewId) {
      link.classList.add('active');
    }
  });

  // Trigger lazy loading
  if (viewId === 'journeys-view') {
    loadUserJourneys();
  } else if (viewId === 'admin-view') {
    loadAdminDashboard();
  }
}

function updateAuthUI() {
  const user = api.getUser();
  const authContainer = document.getElementById('nav-auth-container');
  const adminNav = document.getElementById('nav-admin-link');
  if (!authContainer) return;

  if (user) {
    authContainer.innerHTML = `
      <div style="position: relative; display: inline-block;">
        <button class="user-profile-btn" onclick="toggleUserDropdown()">
          <div class="user-avatar">${user.full_name.charAt(0).toUpperCase()}</div>
          <span>${user.full_name.split(' ')[0]}</span>
          <i class="fa-solid fa-chevron-down" style="font-size: 0.7rem; color: var(--text-light);"></i>
        </button>
        <div id="user-dropdown-menu" style="display: none; position: absolute; right: 0; top: 120%; background: white; border: 1px solid var(--border); border-radius: 8px; box-shadow: var(--shadow-lg); width: 180px; z-index: 100; overflow: hidden;">
          <div style="padding: 0.75rem 1rem; border-bottom: 1px solid var(--border); font-size: 0.8rem;">
            <strong>${user.full_name}</strong>
            <div style="color: var(--text-muted); font-size: 0.72rem;">${user.email}</div>
          </div>
          <div style="padding: 0.4rem 0;">
            <div style="padding: 0.5rem 1rem; font-size: 0.85rem; cursor: pointer; display: flex; align-items: center; gap: 0.5rem;" onclick="switchView('journeys-view'); toggleUserDropdown();">
              <i class="fa-solid fa-plane"></i> My Journeys
            </div>
            ${user.role === 'admin' ? `
              <div style="padding: 0.5rem 1rem; font-size: 0.85rem; cursor: pointer; display: flex; align-items: center; gap: 0.5rem; color: #1e40af;" onclick="switchView('admin-view'); toggleUserDropdown();">
                <i class="fa-solid fa-gauge"></i> Admin Console
              </div>
            ` : ''}
            <div style="padding: 0.5rem 1rem; font-size: 0.85rem; cursor: pointer; display: flex; align-items: center; gap: 0.5rem; color: #b91c1c; border-top: 1px solid #f1f5f9;" onclick="handleLogout()">
              <i class="fa-solid fa-arrow-right-from-bracket"></i> Log Out
            </div>
          </div>
        </div>
      </div>
    `;

    if (adminNav) {
      adminNav.style.display = user.role === 'admin' ? 'flex' : 'none';
    }
  } else {
    authContainer.innerHTML = `
      <button style="background: transparent; border: 1px solid var(--border); padding: 0.45rem 1rem; border-radius: var(--radius-md); font-weight: 700; font-size: 0.88rem; cursor: pointer;" onclick="openAuthModal('login')">
        Log In
      </button>
      <button style="background: var(--primary); color: white; border: none; padding: 0.45rem 1rem; border-radius: var(--radius-md); font-weight: 700; font-size: 0.88rem; cursor: pointer;" onclick="openAuthModal('register')">
        Sign Up
      </button>
    `;
    if (adminNav) adminNav.style.display = 'none';
  }
}

function toggleUserDropdown() {
  const menu = document.getElementById('user-dropdown-menu');
  if (menu) {
    menu.style.display = menu.style.display === 'none' ? 'block' : 'none';
  }
}

// Modal management
function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.add('open');
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.remove('open');
}

// Auth Handlers
function openAuthModal(tab = 'login') {
  openModal('auth-modal');
  switchAuthTab(tab);
}

function switchAuthTab(tab) {
  const loginForm = document.getElementById('login-form-container');
  const regForm = document.getElementById('register-form-container');
  const tabLogin = document.getElementById('tab-btn-login');
  const tabReg = document.getElementById('tab-btn-register');

  if (tab === 'login') {
    loginForm.style.display = 'block';
    regForm.style.display = 'none';
    tabLogin.style.borderBottom = '2px solid var(--primary)';
    tabLogin.style.color = 'var(--primary)';
    tabReg.style.borderBottom = 'none';
    tabReg.style.color = 'var(--text-muted)';
  } else {
    loginForm.style.display = 'none';
    regForm.style.display = 'block';
    tabReg.style.borderBottom = '2px solid var(--primary)';
    tabReg.style.color = 'var(--primary)';
    tabLogin.style.borderBottom = 'none';
    tabLogin.style.color = 'var(--text-muted)';
  }
}

function togglePasswordVisibility(fieldId, btnEl) {
  const input = document.getElementById(fieldId);
  if (!input) return;

  const isPassword = input.type === 'password';
  input.type = isPassword ? 'text' : 'password';

  if (btnEl) {
    btnEl.innerHTML = isPassword ? '<i class="fa-solid fa-eye-slash"></i>' : '<i class="fa-solid fa-eye"></i>';
  }
}

function updatePasswordLiveValidation() {
  const pwdInput = document.getElementById('register-password');
  const confirmInput = document.getElementById('register-confirm-password');
  if (!pwdInput) return;

  const pwd = pwdInput.value;
  const confirmPwd = confirmInput ? confirmInput.value : '';

  const checks = {
    length: pwd.length >= 8,
    upper: /[A-Z]/.test(pwd),
    lower: /[a-z]/.test(pwd),
    digit: /\d/.test(pwd),
    special: /[^A-Za-z0-9]/.test(pwd),
    match: pwd.length > 0 && pwd === confirmPwd
  };

  const updateItem = (id, isValid) => {
    const el = document.getElementById(id);
    if (!el) return;
    if (isValid) {
      el.className = 'criteria-item valid';
      el.querySelector('i').className = 'fa-solid fa-circle-check';
    } else {
      el.className = 'criteria-item invalid';
      el.querySelector('i').className = 'fa-solid fa-circle';
    }
  };

  updateItem('rule-length', checks.length);
  updateItem('rule-upper', checks.upper);
  updateItem('rule-lower', checks.lower);
  updateItem('rule-digit', checks.digit);
  updateItem('rule-special', checks.special);
  updateItem('rule-match', checks.match);

  return Object.values(checks).every(Boolean);
}

function fillDemoCredentials(role) {
  const emailInput = document.getElementById('login-email');
  const pwdInput = document.getElementById('login-password');
  if (!emailInput || !pwdInput) return;

  if (role === 'admin') {
    emailInput.value = 'admin@flywise.ai';
    pwdInput.value = 'Admin@123';
  } else {
    emailInput.value = 'navaneeth@flywise.ai';
    pwdInput.value = 'Password@123';
  }
}

async function handleLogin(e) {
  e.preventDefault();
  const email = document.getElementById('login-email').value.trim();
  const password = document.getElementById('login-password').value;

  try {
    const data = await api.post('/auth/login', { email, password });
    api.setToken(data.token);
    api.setUser(data.user);
    updateAuthUI();
    closeModal('auth-modal');
    showToast(`Welcome back, ${data.user.full_name}!`, 'success');
    switchView('journeys-view');
  } catch (err) {
    showToast(err.message || 'Login failed', 'danger');
  }
}

async function handleRegister(e) {
  e.preventDefault();
  const name = document.getElementById('register-name').value.trim();
  const email = document.getElementById('register-email').value.trim();
  const password = document.getElementById('register-password').value;
  const confirmPassword = document.getElementById('register-confirm-password').value;
  const phone = document.getElementById('register-phone').value.trim();

  if (password !== confirmPassword) {
    showToast('Passwords do not match. Please verify.', 'danger');
    return;
  }

  // Check complexity
  if (password.length < 8) {
    showToast('Password must be at least 8 characters long.', 'danger');
    return;
  }
  if (!/[A-Z]/.test(password)) {
    showToast('Password must contain at least one uppercase letter (A-Z).', 'danger');
    return;
  }
  if (!/[a-z]/.test(password)) {
    showToast('Password must contain at least one lowercase letter (a-z).', 'danger');
    return;
  }
  if (!/\d/.test(password)) {
    showToast('Password must contain at least one digit (0-9).', 'danger');
    return;
  }
  if (!/[^A-Za-z0-9]/.test(password)) {
    showToast('Password must contain at least one special character (!@#$%^&*).', 'danger');
    return;
  }

  try {
    const data = await api.post('/auth/register', {
      full_name: name,
      email,
      password,
      confirm_password: confirmPassword,
      phone
    });
    api.setToken(data.token);
    api.setUser(data.user);
    updateAuthUI();
    closeModal('auth-modal');
    showToast(`Welcome to FlyWise, ${name}! Your account is ready.`, 'success');
    switchView('journeys-view');
  } catch (err) {
    showToast(err.message || 'Registration failed', 'danger');
  }
}

function handleLogout() {
  api.post('/auth/logout').catch(() => {});
  api.setToken(null);
  api.setUser(null);
  updateAuthUI();
  switchView('home-view');
  showToast('You have been logged out.', 'info');
}

// Quick Route Pre-fill
function setQuickRoute(origin, dest) {
  document.getElementById('search-origin').value = origin;
  document.getElementById('search-destination').value = dest;
  performFlightSearch();
}

function swapAirports() {
  const orig = document.getElementById('search-origin');
  const dest = document.getElementById('search-destination');
  if (orig && dest) {
    const tmp = orig.value;
    orig.value = dest.value;
    dest.value = tmp;
  }
}

// Itemized Cost Breakdown Modal
function openCostBreakdownModal(itineraryId) {
  const it = currentSearchResults.find(i => i.itinerary_id === itineraryId);
  if (!it) return;

  const modal = document.getElementById('cost-modal');
  const body = document.getElementById('cost-modal-body');
  if (!modal || !body) return;

  const cb = it.cost_breakdown;

  body.innerHTML = `
    <h3 style="font-weight: 800; margin-bottom: 0.25rem;">Total Journey Cost Transparency</h3>
    <p style="color: var(--text-muted); font-size: 0.88rem; margin-bottom: 1.5rem;">
      Itemized estimate according to PRD Section 10 preventing hidden surprises.
    </p>

    <div style="background: #f8fafc; border: 1px solid var(--border); border-radius: 12px; padding: 1.25rem; margin-bottom: 1.5rem;">
      <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem; font-size: 0.9rem;">
        <span>Flight Base Fare (${it.airline_name})</span>
        <strong>₹${cb.ticket_fare.base_fare.toLocaleString('en-IN')}</strong>
      </div>
      <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem; font-size: 0.9rem;">
        <span>Taxes & Mandatory Airport Fees</span>
        <strong>₹${(cb.ticket_fare.taxes + cb.ticket_fare.mandatory_fees).toLocaleString('en-IN')}</strong>
      </div>
      <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem; font-size: 0.9rem;">
        <span>Checked Baggage (${cb.baggage_charges.included_kg}kg free included)</span>
        <strong>₹${cb.baggage_charges.charge.toLocaleString('en-IN')}</strong>
      </div>
      <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem; font-size: 0.9rem;">
        <span>Standard Seat Selection (${cb.seat_charges.seat_type})</span>
        <strong>₹${cb.seat_charges.charge.toLocaleString('en-IN')}</strong>
      </div>
      <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem; font-size: 0.9rem; color: #0284c7;">
        <span>Estimated Ground Transport (Origin & Dest Cabs)</span>
        <strong>₹${cb.ground_transport.subtotal.toLocaleString('en-IN')}</strong>
      </div>

      <div style="display: flex; justify-content: space-between; border-top: 2px dashed var(--border); padding-top: 0.75rem; margin-top: 0.75rem; font-size: 1.3rem; font-weight: 800;">
        <span>Estimated Overall Journey Total</span>
        <span style="color: var(--primary);">₹${cb.estimated_total_journey_cost.toLocaleString('en-IN')}</span>
      </div>
    </div>

    <button class="btn-search" style="width: 100%;" onclick="closeModal('cost-modal'); startBookingFlow('${it.itinerary_id}')">
      Proceed with this Itinerary
    </button>
  `;

  openModal('cost-modal');
}

function explainFlightScore(itineraryId) {
  const it = currentSearchResults.find(i => i.itinerary_id === itineraryId);
  if (!it) return;

  const modal = document.getElementById('cost-modal');
  const body = document.getElementById('cost-modal-body');
  if (!modal || !body) return;

  const br = it.score_breakdown;

  body.innerHTML = `
    <h3 style="font-weight: 800; margin-bottom: 0.25rem;">Recommendation Score: ${it.recommendation_score} / 100</h3>
    <p style="color: var(--text-muted); font-size: 0.88rem; margin-bottom: 1.5rem;">
      Calculated using the 5-factor normalized model (PRD Section 9.3) based on your priorities.
    </p>

    <div style="display: flex; flex-direction: column; gap: 0.85rem; margin-bottom: 1.5rem;">
      <div>
        <div style="display: flex; justify-content: space-between; font-size: 0.85rem; font-weight: 700; margin-bottom: 4px;">
          <span>Journey Cost Match (Weight 30%)</span>
          <span>${br.cost_score} / 100</span>
        </div>
        <div style="height: 8px; background: #e2e8f0; border-radius: 9999px; overflow: hidden;">
          <div style="width: ${br.cost_score}%; background: #10b981; height: 100%;"></div>
        </div>
      </div>

      <div>
        <div style="display: flex; justify-content: space-between; font-size: 0.85rem; font-weight: 700; margin-bottom: 4px;">
          <span>Duration & Efficiency (Weight 20%)</span>
          <span>${br.duration_score} / 100</span>
        </div>
        <div style="height: 8px; background: #e2e8f0; border-radius: 9999px; overflow: hidden;">
          <div style="width: ${br.duration_score}%; background: #0284c7; height: 100%;"></div>
        </div>
      </div>

      <div>
        <div style="display: flex; justify-content: space-between; font-size: 0.85rem; font-weight: 700; margin-bottom: 4px;">
          <span>Connection Safety (Weight 20%)</span>
          <span>${br.safety_score} / 100</span>
        </div>
        <div style="height: 8px; background: #e2e8f0; border-radius: 9999px; overflow: hidden;">
          <div style="width: ${br.safety_score}%; background: #f59e0b; height: 100%;"></div>
        </div>
      </div>

      <div>
        <div style="display: flex; justify-content: space-between; font-size: 0.85rem; font-weight: 700; margin-bottom: 4px;">
          <span>Schedule Convenience (Weight 15%)</span>
          <span>${br.convenience_score} / 100</span>
        </div>
        <div style="height: 8px; background: #e2e8f0; border-radius: 9999px; overflow: hidden;">
          <div style="width: ${br.convenience_score}%; background: #8b5cf6; height: 100%;"></div>
        </div>
      </div>

      <div>
        <div style="display: flex; justify-content: space-between; font-size: 0.85rem; font-weight: 700; margin-bottom: 4px;">
          <span>User Preferences Match (Weight 15%)</span>
          <span>${br.preference_score} / 100</span>
        </div>
        <div style="height: 8px; background: #e2e8f0; border-radius: 9999px; overflow: hidden;">
          <div style="width: ${br.preference_score}%; background: #ec4899; height: 100%;"></div>
        </div>
      </div>
    </div>

    <button class="btn-search" style="width: 100%;" onclick="closeModal('cost-modal')">
      Got It
    </button>
  `;

  openModal('cost-modal');
}
