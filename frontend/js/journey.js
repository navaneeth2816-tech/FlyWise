/**
 * FlyWise - Post-Booking Journey Companion & Digital Twin Module
 */

let activeJourney = null;

async function loadUserJourneys() {
  const container = document.getElementById('journeys-container');
  if (!container) return;

  const user = api.getUser();
  if (!user) {
    container.innerHTML = `
      <div style="background: white; border-radius: var(--radius-lg); padding: 4rem 2rem; text-align: center; border: 1px solid var(--border); box-shadow: var(--shadow-sm); max-width: 600px; margin: 0 auto;">
        <div style="width: 64px; height: 64px; border-radius: 50%; background: #eff6ff; color: var(--primary); display: flex; align-items: center; justify-content: center; font-size: 2rem; margin: 0 auto 1.25rem;">
          <i class="fa-solid fa-user-lock"></i>
        </div>
        <h3 style="font-weight: 800; font-size: 1.4rem; margin-bottom: 0.5rem;">Log In to View Your Dashboard</h3>
        <p style="color: var(--text-muted); font-size: 0.95rem; margin-bottom: 1.75rem; line-height: 1.5;">
          Access your dynamic 10-stage flight digital twin, interactive checklists, real-time alerts, and booking records.
        </p>
        <div style="display: flex; gap: 1rem; justify-content: center;">
          <button class="btn-search" onclick="openAuthModal('login')">
            <i class="fa-solid fa-arrow-right-to-bracket"></i> Sign In
          </button>
          <button style="background: white; border: 1px solid var(--border); padding: 0.75rem 1.4rem; border-radius: var(--radius-md); font-weight: 700; cursor: pointer;" onclick="openAuthModal('register')">
            Create Account
          </button>
        </div>
      </div>
    `;
    return;
  }

  container.innerHTML = `
    <div style="text-align: center; padding: 3rem 1rem;">
      <i class="fa-solid fa-spinner fa-spin" style="font-size: 2rem; color: var(--primary);"></i>
      <p style="color: var(--text-muted); margin-top: 0.5rem;">Synchronizing your journey companion...</p>
    </div>
  `;

  try {
    // 1. Fetch fresh profile info from /auth/me
    let userProfile = user;
    try {
      const meData = await api.get('/auth/me');
      if (meData.user) {
        userProfile = meData.user;
        api.setUser(userProfile);
      }
    } catch (e) {}

    // 2. Fetch journeys from MySQL
    const data = await api.get('/journeys');
    const journeys = data.journeys || [];

    renderJourneysDashboard(container, userProfile, journeys);
  } catch (err) {
    container.innerHTML = `
      <div style="text-align: center; padding: 3rem 1rem; color: var(--danger);">
        <i class="fa-solid fa-triangle-exclamation" style="font-size: 2rem; margin-bottom: 0.5rem;"></i>
        <p style="font-weight: 700;">${err.message || 'Error loading dashboard'}</p>
      </div>
    `;
  }
}

function renderJourneysDashboard(container, user, journeys) {
  const memberSince = user.created_at ? new Date(user.created_at).toLocaleDateString('en-IN', { month: 'short', year: 'numeric' }) : '2026';
  const roleBadge = user.role === 'admin' ? '<span class="admin-badge"><i class="fa-solid fa-shield-halved"></i> Administrator</span>' : '<span class="user-badge"><i class="fa-solid fa-check"></i> Verified Traveller</span>';

  // 1. User Profile Header Card
  const profileHeaderHtml = `
    <div class="user-profile-header-card">
      <div class="profile-left">
        <div class="profile-avatar-lg">${user.full_name.charAt(0).toUpperCase()}</div>
        <div>
          <div style="margin-bottom: 0.25rem;">${roleBadge}</div>
          <h2 class="profile-name">${user.full_name}</h2>
          <div class="profile-meta">
            <span><i class="fa-solid fa-envelope"></i> ${user.email}</span>
            ${user.phone ? `<span><i class="fa-solid fa-phone"></i> ${user.phone}</span>` : ''}
            <span><i class="fa-solid fa-language"></i> ${user.preferred_language ? user.preferred_language.toUpperCase() : 'EN'}</span>
            <span><i class="fa-solid fa-calendar-check"></i> Member since ${memberSince}</span>
          </div>
        </div>
      </div>
      <div class="profile-stats">
        <div class="stat-box">
          <span class="stat-number">${journeys.length}</span>
          <span class="stat-label">Total Bookings</span>
        </div>
        <div class="stat-box">
          <span class="stat-number">${journeys.filter(j => j.journey_status !== 'completed' && j.journey_status !== 'cancelled').length}</span>
          <span class="stat-label">Active Journeys</span>
        </div>
      </div>
    </div>
  `;

  // 2. If user has NO bookings: Helpful informative empty state
  if (journeys.length === 0) {
    container.innerHTML = `
      ${profileHeaderHtml}
      <div class="dashboard-empty-card">
        <div class="empty-icon-circle">
          <i class="fa-solid fa-plane-slash"></i>
        </div>
        <h3 style="font-weight: 800; font-size: 1.35rem; margin-bottom: 0.5rem; color: var(--text-main);">No Bookings Found Yet</h3>
        <p style="color: var(--text-muted); max-width: 540px; margin: 0 auto 1.75rem; font-size: 0.92rem; line-height: 1.5;">
          Hello <strong>${user.full_name}</strong>, you don't have any flight reservations recorded under your account. Explore flights from Tirupati, Delhi, Mumbai, Bengaluru and more to activate your dynamic Digital Twin and automated journey tracking.
        </p>
        <div style="display: flex; gap: 1rem; justify-content: center; flex-wrap: wrap;">
          <button class="btn-search" onclick="switchView('home-view')">
            <i class="fa-solid fa-magnifying-glass"></i> Search Flights Now
          </button>
          <button class="btn-ai-pill" onclick="toggleAiDrawer(); sendSuggestedPrompt('Find flights from Tirupati to Delhi under ₹7,000');">
            <i class="fa-solid fa-wand-magic-sparkles"></i> Plan Trip with FlyWise AI
          </button>
        </div>
      </div>
    `;
    return;
  }

  // 3. User HAS bookings: Render Trips Layout
  container.innerHTML = `
    ${profileHeaderHtml}

    <div style="display: grid; grid-template-columns: 340px 1fr; gap: 2rem; margin-top: 2rem;">
      <!-- Journeys sidebar list -->
      <div style="display: flex; flex-direction: column; gap: 1rem;">
        <h3 style="font-weight: 800; font-size: 1.15rem; margin-bottom: 0.25rem;">
          <i class="fa-solid fa-ticket" style="color: var(--primary);"></i> Your Booked Journeys (${journeys.length})
        </h3>
        ${journeys.map((j) => `
          <div class="flight-card journey-item-card" style="padding: 1.1rem; cursor: pointer; border-left: 4px solid ${j.journey_status === 'disrupted' ? '#ef4444' : '#1e40af'};" onclick="viewJourneyDetails(${j.journey_id})">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem;">
              <span style="font-weight: 800; color: var(--primary); font-size: 0.95rem;">${j.booking_reference}</span>
              <span class="risk-badge ${j.journey_status === 'disrupted' ? 'HIGH' : 'LOW'}">${j.journey_status.toUpperCase()}</span>
            </div>
            <div style="font-weight: 700; font-size: 1.05rem;">
              ${j.origin_city} (${j.origin_code}) → ${j.destination_city} (${j.destination_code})
            </div>
            <div style="font-size: 0.8rem; color: var(--text-muted); margin-top: 0.35rem; display: flex; justify-content: space-between;">
              <span>${j.airline_name} • ${j.flight_number}</span>
              <span>₹${Number(j.total_amount).toLocaleString('en-IN')}</span>
            </div>
            <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.25rem;">
              <i class="fa-solid fa-calendar"></i> ${new Date(j.planned_departure).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
            </div>
          </div>
        `).join('')}
      </div>

      <!-- Main Journey Detail & Digital Twin Container -->
      <div id="journey-detail-pane">
        <!-- Injected by viewJourneyDetails -->
      </div>
    </div>
  `;

  // Select first journey by default
  viewJourneyDetails(journeys[0].journey_id);
}

async function viewJourneyDetails(journeyId) {
  const pane = document.getElementById('journey-detail-pane');
  if (!pane) return;

  pane.innerHTML = `
    <div style="text-align: center; padding: 4rem;">
      <i class="fa-solid fa-spinner fa-spin" style="font-size: 2rem; color: var(--primary);"></i>
      <p style="color: var(--text-muted); margin-top: 0.5rem;">Synchronizing Digital Twin state...</p>
    </div>
  `;

  try {
    const data = await api.get(`/journeys/${journeyId}`);
    activeJourney = data.journey;
    renderJourneyDetails(pane, activeJourney);
  } catch (err) {
    pane.innerHTML = `<div style="color: var(--danger); font-weight: 700;">${err.message}</div>`;
  }
}

function renderJourneyDetails(container, j) {
  const isDisrupted = j.journey_status === 'disrupted' || j.flight_status === 'delayed';

  container.innerHTML = `
    <!-- Top Action Card -->
    <div style="background: white; border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 1.75rem; margin-bottom: 1.5rem; box-shadow: var(--shadow-sm);">
      <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.5rem; flex-wrap: wrap; gap: 1rem;">
        <div>
          <span style="font-size: 0.8rem; font-weight: 800; color: var(--text-muted); letter-spacing: 0.5px;">ACTIVE JOURNEY COMPANION</span>
          <h2 style="font-weight: 800; font-size: 1.6rem; color: var(--text-main); margin-top: 0.25rem;">
            ${j.origin_city} (${j.origin_code}) to ${j.destination_city} (${j.destination_code})
          </h2>
          <div style="font-size: 0.9rem; color: var(--text-muted); margin-top: 0.25rem;">
            PNR: <strong>${j.booking_reference}</strong> • Flight: <strong>${j.flight_number}</strong> (${j.airline_name}) • Fare Paid: <strong>₹${Number(j.total_amount).toLocaleString('en-IN')}</strong>
          </div>
        </div>

        <div style="display: flex; gap: 0.75rem;">
          <button style="background: white; border: 1px solid var(--border); padding: 0.55rem 1rem; border-radius: var(--radius-md); font-weight: 700; cursor: pointer;" onclick="openTicketModalForBooking('${j.booking_reference}')">
            <i class="fa-solid fa-print"></i> View / Print Ticket
          </button>
          ${isDisrupted ? `
            <button class="emergency-btn-cta" style="box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);" onclick="activateEmergencyMode(${j.journey_id})">
              <i class="fa-solid fa-triangle-exclamation"></i> Emergency Travel Mode
            </button>
          ` : ''}
          <button style="background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; padding: 0.55rem 1rem; border-radius: var(--radius-md); font-weight: 700; cursor: pointer;" onclick="openCancellationModal(${j.booking_id})">
            Cancel Booking
          </button>
        </div>
      </div>

      ${isDisrupted ? `
        <div style="background: #fef2f2; border-left: 4px solid #ef4444; padding: 1rem; border-radius: 8px; margin-bottom: 1.5rem; display: flex; justify-content: space-between; align-items: center;">
          <div>
            <strong style="color: #991b1b;"><i class="fa-solid fa-circle-exclamation"></i> Flight Delay Detected!</strong>
            <p style="font-size: 0.85rem; color: #7f1d1d; margin-top: 2px;">Your incoming flight has a delay recorded. Click Emergency Travel Mode for alternative discovery & DGCA passenger assistance.</p>
          </div>
          <button class="emergency-btn-cta" style="font-size: 0.82rem; padding: 0.4rem 0.9rem;" onclick="activateEmergencyMode(${j.journey_id})">
            Resolve Disruption
          </button>
        </div>
      ` : ''}

      <!-- Digital Twin 10-Stage Dynamic Timeline -->
      <h4 style="font-weight: 800; font-size: 0.95rem; margin-bottom: 1rem;">
        <i class="fa-solid fa-network-wired" style="color: var(--primary);"></i> Flight Journey Digital Twin
      </h4>
      <div class="timeline-track">
        ${j.digital_twin.stages.map((st, idx) => {
          let stateClass = '';
          if (idx < j.digital_twin.current_index) stateClass = 'completed';
          else if (idx === j.digital_twin.current_index) stateClass = isDisrupted ? 'disrupted' : 'active';

          return `
            <div class="timeline-step ${stateClass}">
              <div class="step-node">${idx < j.digital_twin.current_index ? '✓' : idx + 1}</div>
              <div class="step-label">${st.label}</div>
            </div>
          `;
        }).join('')}
      </div>
    </div>

    <!-- Interactive Travel Checklist & Events Section -->
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem;">
      <!-- Interactive Checklist -->
      <div style="background: white; border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 1.5rem;">
        <h4 style="font-weight: 800; margin-bottom: 1rem;">
          <i class="fa-solid fa-list-check" style="color: #10b981;"></i> Pre-Departure Checklist
        </h4>
        <div id="journey-checklist-items" style="display: flex; flex-direction: column; gap: 0.75rem;">
          <label class="filter-checkbox-label" style="background: #f8fafc; padding: 0.65rem; border-radius: 8px;">
            <input type="checkbox" checked>
            <span>Government Photo ID verified (Aadhaar / Voter ID / Passport)</span>
          </label>
          <label class="filter-checkbox-label" style="background: #f8fafc; padding: 0.65rem; border-radius: 8px;">
            <input type="checkbox">
            <span>Web Check-In completed (opens 48h prior to departure)</span>
          </label>
          <label class="filter-checkbox-label" style="background: #f8fafc; padding: 0.65rem; border-radius: 8px;">
            <input type="checkbox" checked>
            <span>Baggage weight checked (7kg cabin, 15kg checked)</span>
          </label>
          <label class="filter-checkbox-label" style="background: #f8fafc; padding: 0.65rem; border-radius: 8px;">
            <input type="checkbox">
            <span>Airport transport / metro departure booked</span>
          </label>
        </div>
      </div>

      <!-- Real-time Journey Events History -->
      <div style="background: white; border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 1.5rem;">
        <h4 style="font-weight: 800; margin-bottom: 1rem;">
          <i class="fa-solid fa-satellite-dish" style="color: var(--accent);"></i> Journey Event Log
        </h4>
        <div style="display: flex; flex-direction: column; gap: 0.75rem; max-height: 250px; overflow-y: auto;">
          ${j.events && j.events.length > 0 ? j.events.map(ev => `
            <div style="border-left: 2px solid var(--primary); padding-left: 0.75rem;">
              <div style="font-size: 0.75rem; color: var(--text-muted);">${new Date(ev.event_timestamp).toLocaleString()}</div>
              <div style="font-size: 0.88rem; font-weight: 600; color: var(--text-main);">${ev.event_description}</div>
            </div>
          `).join('') : '<p style="color: var(--text-muted); font-size: 0.85rem;">No events logged yet.</p>'}
        </div>
      </div>
    </div>
  `;
}

async function activateEmergencyMode(journeyId) {
  const modal = document.getElementById('emergency-modal');
  const body = document.getElementById('emergency-modal-body');
  if (!modal || !body) return;

  body.innerHTML = `
    <div style="text-align: center; padding: 2rem;">
      <i class="fa-solid fa-spinner fa-spin" style="font-size: 2rem; color: var(--danger);"></i>
      <p style="margin-top: 0.5rem;">Activating Emergency Travel Mode & searching alternative routes...</p>
    </div>
  `;
  openModal('emergency-modal');

  try {
    const data = await api.post(`/journeys/${journeyId}/emergency-mode`);
    const j = data.journey;
    const rec = data.recovery_options;

    body.innerHTML = `
      <div style="border-bottom: 2px solid #fecaca; padding-bottom: 1rem; margin-bottom: 1.5rem;">
        <span style="background: #ef4444; color: white; padding: 2px 8px; border-radius: 9999px; font-size: 0.75rem; font-weight: 800;">EMERGENCY TRAVEL RADAR</span>
        <h2 style="color: #991b1b; font-weight: 800; margin-top: 0.25rem;">Disruption Crisis Guidance</h2>
        <p style="color: var(--text-muted); font-size: 0.9rem;">Affected Flight: <strong>${j.flight_number}</strong> (${j.airline_name}) • PNR: <strong>${j.booking_reference}</strong></p>
      </div>

      <!-- Alternative Itineraries Discovered -->
      <h4 style="font-weight: 800; margin-bottom: 0.75rem;"><i class="fa-solid fa-radar" style="color: var(--primary);"></i> ${rec.summary}</h4>
      <div style="display: flex; flex-direction: column; gap: 0.75rem; margin-bottom: 1.5rem;">
        ${rec.alternatives && rec.alternatives.length > 0 ? rec.alternatives.map(alt => `
          <div style="border: 1px solid var(--border); border-radius: 8px; padding: 0.85rem; display: flex; justify-content: space-between; align-items: center; background: #f8fafc;">
            <div>
              <strong style="color: var(--primary);">${alt.airline_name} (${alt.flight_number})</strong>
              <div style="font-size: 0.8rem; color: var(--text-muted);">
                Departs: ${new Date(alt.scheduled_departure).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} • Available Seats: ${alt.available_seats}
              </div>
            </div>
            <div style="text-align: right;">
              <div style="font-weight: 800; font-size: 1.1rem;">₹${Number(alt.base_fare).toLocaleString('en-IN')}</div>
              <button class="btn-select-flight" style="font-size: 0.75rem; padding: 4px 10px; margin-top: 4px;" onclick="showToast('Rebooking protection inquiry registered with airline.', 'info')">
                Request Rebook
              </button>
            </div>
          </div>
        `).join('') : '<p style="color: var(--text-muted);">No immediate same-airline alternatives available.</p>'}
      </div>

      <!-- DGCA Passenger Rights -->
      <h4 style="font-weight: 800; margin-bottom: 0.5rem;"><i class="fa-solid fa-shield-halved" style="color: #059669;"></i> Your Statutory Rights (DGCA CAR Section 3)</h4>
      <ul style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 1.5rem; padding-left: 1.25rem;">
        ${data.passenger_rights.map(r => `<li>${r}</li>`).join('')}
      </ul>

      <!-- Support Contacts -->
      <div style="background: #fffbeb; border: 1px solid #fde68a; padding: 1rem; border-radius: 8px; font-size: 0.85rem;">
        <strong><i class="fa-solid fa-headset"></i> Immediate Support:</strong>
        <div style="margin-top: 0.25rem;">• ${data.support_contacts.airline_support}</div>
        <div>• ${data.support_contacts.airport_helpdesk}</div>
        <div>• ${data.support_contacts.dgca_airsewa}</div>
      </div>
    `;
  } catch (err) {
    body.innerHTML = `<div style="color: var(--danger);">${err.message}</div>`;
  }
}

async function openCancellationModal(bookingId) {
  if (!confirm('Are you sure you want to cancel this booking? A standard cancellation fee applies, and your seat will be released immediately.')) {
    return;
  }

  try {
    const res = await api.post(`/bookings/${bookingId}/cancel`, { reason: 'Passenger requested cancellation' });
    showToast(`Booking cancelled. Refund of ₹${res.cancellation.refund_amount.toLocaleString('en-IN')} initiated.`, 'success');
    loadUserJourneys();
  } catch (err) {
    showToast(err.message || 'Error cancelling booking', 'danger');
  }
}
