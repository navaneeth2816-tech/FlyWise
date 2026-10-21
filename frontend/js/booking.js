/**
 * FlyWise AI - Multi-Step Booking Wizard, Demonstration OTP, Simulated Checkout & Airline Ticket
 */

let activeBookingItinerary = null;
let selectedSeat = null;
let currentFlightSeats = [];
let bookingWizardStep = 1; // Step 1: Passenger & Seat, Step 2: Demo OTP, Step 3: Summary & Demo Payment
let bookingPassengerData = null; // { full_name, email, phone, gender, date_of_birth, addons }
let activeDemoOtp = null; // 6-digit demonstration OTP from backend
let activeVerificationRequestId = null; // Unique server-side verification request ID
let bookingVerificationToken = null; // Single-use verification token from backend
let selectedPaymentMode = 'card'; // 'card', 'upi', 'qr', 'netbanking'
let isOtpSending = false;
let isOtpVerifying = false;
let isBookingSubmitting = false;

/**
 * Initializes the booking flow for the selected itinerary.
 */
async function startBookingFlow(itineraryId, triggerBtn = null) {
  let it = (typeof currentSearchResults !== 'undefined' ? currentSearchResults : []).find(item => item.itinerary_id === itineraryId);
  if (!it && typeof window !== 'undefined' && window.currentSearchResults) {
    it = window.currentSearchResults.find(item => item.itinerary_id === itineraryId);
  }
  if (!it) {
    showToast('Itinerary details not found. Please refresh search results.', 'danger');
    return;
  }

  // Provide immediate button feedback if button element was passed
  let originalBtnHtml = '';
  if (triggerBtn) {
    originalBtnHtml = triggerBtn.innerHTML;
    triggerBtn.disabled = true;
    triggerBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Selecting...';
  }
  
  // Reset booking wizard state
  activeBookingItinerary = it;
  selectedSeat = null;
  bookingWizardStep = 1;
  bookingPassengerData = null;
  activeDemoOtp = null;
  activeVerificationRequestId = null;
  bookingVerificationToken = null;
  selectedPaymentMode = 'card';
  isBookingSubmitting = false;

  // Persist selected flight in session so user doesn't lose progress if they log in
  try {
    sessionStorage.setItem('flywise_pending_booking', itineraryId);
  } catch (e) {}

  const modal = document.getElementById('booking-modal');
  const body = document.getElementById('booking-modal-body');
  if (!modal || !body) return;

  // Display immediate loading state inside modal for perceived responsiveness
  body.innerHTML = `
    <div style="text-align: center; padding: 3.5rem 1rem;">
      <i class="fa-solid fa-plane-departure fa-spin" style="font-size: 2.4rem; color: var(--primary); margin-bottom: 1rem;"></i>
      <h3 style="font-weight: 800; color: #1e3a8a; margin-bottom: 0.5rem;">Preparing Flight Reservation...</h3>
      <p style="color: var(--text-muted); font-size: 0.9rem;">
        Loading live seat map for <strong>${it.airline_name} (${it.segments[0].flight_number})</strong> • ${it.origin_code} → ${it.destination_code}
      </p>
    </div>
  `;
  openModal('booking-modal');

  const firstFlightId = it.segments && it.segments[0] ? it.segments[0].flight_id : null;
  
  // Load seats for this flight from MySQL
  try {
    if (firstFlightId) {
      const seatData = await api.get(`/flights/${firstFlightId}/seats`);
      currentFlightSeats = seatData.seats || [];
    } else {
      currentFlightSeats = [];
    }
  } catch (err) {
    console.warn('Seat map loading notice:', err);
    currentFlightSeats = [];
  } finally {
    if (triggerBtn) {
      triggerBtn.disabled = false;
      triggerBtn.innerHTML = originalBtnHtml;
    }
  }

  renderBookingWizard();
}
window.startBookingFlow = startBookingFlow;

/**
 * Main dispatcher to render the appropriate wizard step.
 */
function renderBookingWizard() {
  const body = document.getElementById('booking-modal-body');
  if (!body || !activeBookingItinerary) return;

  if (bookingWizardStep === 1) {
    renderStep1PassengerAndSeat(body, activeBookingItinerary);
  } else if (bookingWizardStep === 2) {
    renderStep2DemonstrationOtp(body, activeBookingItinerary);
  } else if (bookingWizardStep === 3) {
    renderStep3SummaryAndPayment(body, activeBookingItinerary);
  }
}

/**
 * Returns HTML for the multi-step progress stepper.
 */
function renderWizardStepperHtml(currentStep) {
  return `
    <div class="booking-wizard-stepper">
      <div class="wizard-step ${currentStep >= 1 ? (currentStep > 1 ? 'completed' : 'active') : ''}">
        <span class="step-num">${currentStep > 1 ? '<i class="fa-solid fa-check"></i>' : '1'}</span>
        <span>Passenger & Seat</span>
      </div>
      <div class="step-divider ${currentStep > 1 ? 'active' : ''}"></div>
      <div class="wizard-step ${currentStep >= 2 ? (currentStep > 2 ? 'completed' : 'active') : ''}">
        <span class="step-num">${currentStep > 2 ? '<i class="fa-solid fa-check"></i>' : '2'}</span>
        <span>Mobile OTP (Demo)</span>
      </div>
      <div class="step-divider ${currentStep > 2 ? 'active' : ''}"></div>
      <div class="wizard-step ${currentStep === 3 ? 'active' : ''}">
        <span class="step-num">3</span>
        <span>Summary & Payment</span>
      </div>
    </div>
  `;
}

// ==========================================================================
// STEP 1: PASSENGER DETAILS & INTERACTIVE SEAT MAP
// ==========================================================================

function renderStep1PassengerAndSeat(container, it) {
  const depTime = new Date(it.departure_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  const arrTime = new Date(it.arrival_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  const user = api.getUser();

  // Restore existing passenger data or defaults
  const pName = bookingPassengerData ? bookingPassengerData.full_name : (user ? user.full_name : 'Navaneeth Naidu');
  const pEmail = bookingPassengerData ? bookingPassengerData.email : (user ? user.email : 'navaneeth@flywise.ai');
  const pPhone = bookingPassengerData ? bookingPassengerData.phone : (user ? (user.phone || '+91 9876543210') : '+91 9876543210');
  const pGender = bookingPassengerData ? bookingPassengerData.gender : 'M';
  const pDob = bookingPassengerData ? bookingPassengerData.date_of_birth : '2003-08-15';
  const hasMeal = bookingPassengerData && bookingPassengerData.addons ? bookingPassengerData.addons.meal : false;
  const hasInsurance = bookingPassengerData && bookingPassengerData.addons ? bookingPassengerData.addons.insurance : false;
  const hasPriority = bookingPassengerData && bookingPassengerData.addons ? bookingPassengerData.addons.priority : false;

  container.innerHTML = `
    ${renderWizardStepperHtml(1)}

    <div style="border-bottom: 1px solid var(--border); padding-bottom: 0.75rem; margin-bottom: 1.25rem;">
      <h3 style="font-weight: 800; margin-bottom: 0.25rem;">Step 1: Enter Passenger Information & Choose Seat</h3>
      <p style="color: var(--text-muted); font-size: 0.88rem;">
        Flight <strong>${it.airline_name} (${it.segments[0].flight_number})</strong> • ${it.origin_city} (${it.origin_code}) → ${it.destination_city} (${it.destination_code}) • ${depTime} - ${arrTime}
      </p>
    </div>

    <div style="display: grid; grid-template-columns: 1.35fr 1fr; gap: 1.75rem;">
      <!-- Left Column: Passenger Details & Add-ons -->
      <div>
        <h4 style="font-weight: 700; margin-bottom: 0.85rem;"><i class="fa-solid fa-user-plus" style="color: var(--primary);"></i> Passenger Details</h4>
        
        <div class="form-group" style="margin-bottom: 0.85rem;">
          <label style="font-weight: 600; font-size: 0.84rem;">Full Name (as per Govt Photo ID) <span style="color: #dc2626;">*</span></label>
          <input type="text" id="passenger-name" value="${pName}" style="padding: 0.65rem; border: 1px solid var(--border); border-radius: 8px; width: 100%; font-weight: 600;" required>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.85rem; margin-bottom: 0.85rem;">
          <div class="form-group">
            <label style="font-weight: 600; font-size: 0.84rem;">Gender</label>
            <select id="passenger-gender" style="padding: 0.65rem; border: 1px solid var(--border); border-radius: 8px; width: 100%;">
              <option value="M" ${pGender === 'M' ? 'selected' : ''}>Male</option>
              <option value="F" ${pGender === 'F' ? 'selected' : ''}>Female</option>
              <option value="Other" ${pGender === 'Other' ? 'selected' : ''}>Other</option>
            </select>
          </div>
          <div class="form-group">
            <label style="font-weight: 600; font-size: 0.84rem;">Date of Birth</label>
            <input type="date" id="passenger-dob" value="${pDob}" style="padding: 0.65rem; border: 1px solid var(--border); border-radius: 8px; width: 100%;">
          </div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.85rem; margin-bottom: 1.25rem;">
          <div class="form-group">
            <label style="font-weight: 600; font-size: 0.84rem;">Email Address <span style="color: #dc2626;">*</span></label>
            <input type="email" id="passenger-email" value="${pEmail}" style="padding: 0.65rem; border: 1px solid var(--border); border-radius: 8px; width: 100%;" required>
          </div>
          <div class="form-group">
            <label style="font-weight: 600; font-size: 0.84rem;">Mobile Number <span style="color: #dc2626;">*</span></label>
            <input type="tel" id="passenger-phone" value="${pPhone}" placeholder="+91 9876543210" style="padding: 0.65rem; border: 1px solid var(--border); border-radius: 8px; width: 100%;" required>
          </div>
        </div>

        <!-- Optional Add-ons -->
        <h4 style="font-weight: 700; margin-bottom: 0.65rem;"><i class="fa-solid fa-cube" style="color: var(--primary);"></i> Journey Enhancements</h4>
        <div style="display: flex; flex-direction: column; gap: 0.5rem; margin-bottom: 1.25rem;">
          <label class="filter-checkbox-label" style="background: #f8fafc; padding: 0.65rem; border-radius: 8px; border: 1px solid var(--border);">
            <input type="checkbox" id="addon-meal" onchange="updateBookingTotal()" ${hasMeal ? 'checked' : ''}>
            <span><strong>Hot Gourmet Meal (+₹350)</strong> — Pre-order fresh hot meal & beverage</span>
          </label>
          <label class="filter-checkbox-label" style="background: #f8fafc; padding: 0.65rem; border-radius: 8px; border: 1px solid var(--border);">
            <input type="checkbox" id="addon-insurance" onchange="updateBookingTotal()" ${hasInsurance ? 'checked' : ''}>
            <span><strong>Comprehensive Travel Insurance (+₹199)</strong> — Trip delay & baggage loss cover up to ₹25,000</span>
          </label>
          <label class="filter-checkbox-label" style="background: #f8fafc; padding: 0.65rem; border-radius: 8px; border: 1px solid var(--border);">
            <input type="checkbox" id="addon-priority" onchange="updateBookingTotal()" ${hasPriority ? 'checked' : ''}>
            <span><strong>Priority Baggage & Boarding (+₹300)</strong> — First off luggage delivery & priority gate access</span>
          </label>
        </div>
      </div>

      <!-- Right Column: Interactive Seat Map & Fare Breakdown -->
      <div style="background: #f8fafc; border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 1.25rem;">
        <h4 style="font-weight: 700; margin-bottom: 0.4rem; display: flex; justify-content: space-between;">
          <span>Aircraft Seat Map</span>
          <span id="selected-seat-badge" style="font-size: 0.8rem; background: var(--primary-light); color: var(--primary); padding: 2px 8px; border-radius: 4px;">
            ${selectedSeat ? `Seat ${selectedSeat.seat_number} (+₹${selectedSeat.cost})` : 'Select a seat'}
          </span>
        </h4>
        <p style="font-size: 0.74rem; color: var(--text-muted); margin-bottom: 0.85rem;">
          Row 1: Extra Legroom (₹600) • Rows 2-6: Window/Aisle (₹250), Middle (Free)
        </p>

        <!-- Seat map visual layout -->
        <div style="background: white; border: 1px solid var(--border); border-radius: 12px; padding: 0.85rem 0.5rem; margin-bottom: 1.15rem; max-height: 250px; overflow-y: auto;">
          <div style="text-align: center; font-size: 0.7rem; font-weight: 800; color: var(--text-muted); letter-spacing: 1px; margin-bottom: 0.5rem;">FRONT / COCKPIT</div>
          <div id="seat-rows-container">
            ${renderSeatGrid(currentFlightSeats)}
          </div>
        </div>

        <!-- Price Summary Breakdown -->
        <div style="border-top: 1px solid var(--border); padding-top: 0.85rem;">
          <div style="display: flex; justify-content: space-between; font-size: 0.84rem; margin-bottom: 0.35rem;">
            <span style="color: var(--text-muted);">Base Airfare</span>
            <span>₹${Number(it.base_fare).toLocaleString('en-IN')}</span>
          </div>
          <div style="display: flex; justify-content: space-between; font-size: 0.84rem; margin-bottom: 0.35rem;">
            <span style="color: var(--text-muted);">Taxes & Airport Fees</span>
            <span>₹${Number(it.taxes + it.mandatory_fees).toLocaleString('en-IN')}</span>
          </div>
          <div style="display: flex; justify-content: space-between; font-size: 0.84rem; margin-bottom: 0.35rem;">
            <span style="color: var(--text-muted);">Seat Fee</span>
            <span id="seat-fee-display">₹${selectedSeat ? selectedSeat.cost : 0}</span>
          </div>
          <div style="display: flex; justify-content: space-between; font-size: 0.84rem; margin-bottom: 0.65rem;">
            <span style="color: var(--text-muted);">Add-ons Subtotal</span>
            <span id="addons-fee-display">₹0</span>
          </div>
          <div style="display: flex; justify-content: space-between; font-size: 1.25rem; font-weight: 800; border-top: 2px dashed var(--border); padding-top: 0.65rem; margin-bottom: 1.15rem;">
            <span>Total Fare</span>
            <span style="color: var(--primary);" id="total-payable-display">₹${Number(it.total_fare).toLocaleString('en-IN')}</span>
          </div>

          <button id="btn-goto-step2" class="btn-search" style="width: 100%; height: 48px; font-size: 0.95rem; font-weight: 700;" onclick="goToBookingStep2()">
            <span>Continue to Mobile Verification</span> <i class="fa-solid fa-arrow-right"></i>
          </button>
        </div>
      </div>
    </div>
  `;

  // Re-highlight selected seat if previously chosen
  if (selectedSeat) {
    const btn = document.getElementById(`seat-btn-${selectedSeat.seat_id}`);
    if (btn) btn.classList.add('selected');
  }
  updateBookingTotal();
}

function renderSeatGrid(seats) {
  if (!seats || seats.length === 0) {
    return '<div style="text-align: center; font-size: 0.85rem; color: var(--text-muted); padding: 1rem;">No seat inventory records found.</div>';
  }

  // Group by row numbers
  const rows = {};
  seats.forEach(s => {
    const rowNum = s.seat_number.replace(/[A-Z]/g, '');
    if (!rows[rowNum]) rows[rowNum] = [];
    rows[rowNum].push(s);
  });

  return Object.keys(rows).map(rowNum => {
    const rowSeats = rows[rowNum];
    const leftGroup = rowSeats.filter(s => ['A', 'B', 'C'].includes(s.seat_number.slice(-1)));
    const rightGroup = rowSeats.filter(s => ['D', 'E', 'F'].includes(s.seat_number.slice(-1)));

    return `
      <div class="seat-row">
        <div class="seat-group">
          ${leftGroup.map(s => renderSeatButton(s)).join('')}
        </div>
        <div class="aisle-gap">${rowNum}</div>
        <div class="seat-group">
          ${rightGroup.map(s => renderSeatButton(s)).join('')}
        </div>
      </div>
    `;
  }).join('');
}

function renderSeatButton(s) {
  const isBooked = s.seat_status === 'booked';
  const isBusiness = s.travel_class === 'business';
  return `
    <button class="seat-btn ${isBooked ? 'booked' : ''} ${isBusiness ? 'business' : ''}" 
            id="seat-btn-${s.seat_id}"
            ${isBooked ? 'disabled' : ''}
            onclick="selectSeat(${s.seat_id}, '${s.seat_number}', '${s.travel_class}')">
      ${s.seat_number}
    </button>
  `;
}

function selectSeat(seatId, seatNumber, travelClass) {
  document.querySelectorAll('.seat-btn.selected').forEach(el => el.classList.remove('selected'));

  const btn = document.getElementById(`seat-btn-${seatId}`);
  if (btn) btn.classList.add('selected');

  // Pricing: Row 1 = 600, Window/Aisle = 250, Middle (B, E) = 0
  let cost = 0;
  if (seatNumber.startsWith('1')) {
    cost = 600;
  } else if (seatNumber.endsWith('B') || seatNumber.endsWith('E')) {
    cost = 0;
  } else {
    cost = 250;
  }

  selectedSeat = {
    seat_id: seatId,
    seat_number: seatNumber,
    cost: cost
  };

  const badge = document.getElementById('selected-seat-badge');
  if (badge) badge.textContent = `Seat ${seatNumber} (+₹${cost})`;

  updateBookingTotal();
}

function updateBookingTotal() {
  if (!activeBookingItinerary) return;

  const baseTotal = activeBookingItinerary.total_fare;
  const seatCost = selectedSeat ? selectedSeat.cost : 0;

  let addonsCost = 0;
  if (document.getElementById('addon-meal') && document.getElementById('addon-meal').checked) addonsCost += 350;
  if (document.getElementById('addon-insurance') && document.getElementById('addon-insurance').checked) addonsCost += 199;
  if (document.getElementById('addon-priority') && document.getElementById('addon-priority').checked) addonsCost += 300;

  const grandTotal = baseTotal + seatCost + addonsCost;

  if (document.getElementById('seat-fee-display')) {
    document.getElementById('seat-fee-display').textContent = `₹${seatCost.toLocaleString('en-IN')}`;
  }
  if (document.getElementById('addons-fee-display')) {
    document.getElementById('addons-fee-display').textContent = `₹${addonsCost.toLocaleString('en-IN')}`;
  }
  if (document.getElementById('total-payable-display')) {
    document.getElementById('total-payable-display').textContent = `₹${grandTotal.toLocaleString('en-IN')}`;
  }
}

/**
 * Validates passenger inputs and navigates to Step 2 (Mobile OTP Verification).
 */
function goToBookingStep2() {
  const user = api.getUser();
  if (!user) {
    showToast('Please sign in to your FlyWise account to continue booking.', 'warning');
    openAuthModal('login');
    return;
  }

  const nameEl = document.getElementById('passenger-name');
  const emailEl = document.getElementById('passenger-email');
  const phoneEl = document.getElementById('passenger-phone');
  const dobEl = document.getElementById('passenger-dob');
  const genderEl = document.getElementById('passenger-gender');

  const name = nameEl ? nameEl.value.trim() : '';
  const email = emailEl ? emailEl.value.trim() : '';
  const phone = phoneEl ? phoneEl.value.trim() : '';
  const dob = dobEl ? dobEl.value : '';
  const gender = genderEl ? genderEl.value : 'M';

  // Validation
  if (!name || name.length < 2) {
    showToast('Please enter a valid passenger full name (at least 2 characters).', 'warning');
    if (nameEl) nameEl.focus();
    return;
  }

  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!email || !emailRegex.test(email)) {
    showToast('Please enter a valid passenger email address.', 'warning');
    if (emailEl) emailEl.focus();
    return;
  }

  const phoneDigits = phone.replace(/\D/g, '');
  if (!phone || phoneDigits.length < 7) {
    showToast('Please enter a valid mobile number for demonstration OTP verification.', 'warning');
    if (phoneEl) phoneEl.focus();
    return;
  }

  // Save validated passenger details
  bookingPassengerData = {
    full_name: name,
    email: email,
    phone: phone,
    gender: gender,
    date_of_birth: dob,
    addons: {
      meal: document.getElementById('addon-meal') ? document.getElementById('addon-meal').checked : false,
      insurance: document.getElementById('addon-insurance') ? document.getElementById('addon-insurance').checked : false,
      priority: document.getElementById('addon-priority') ? document.getElementById('addon-priority').checked : false
    }
  };

  bookingWizardStep = 2;
  renderBookingWizard();

  // Automatically request demonstration OTP from backend if not already active
  if (!activeDemoOtp || !bookingVerificationToken) {
    sendBookingOtp(false);
  }
}

function goToBookingStep1() {
  bookingWizardStep = 1;
  activeDemoOtp = null;
  activeVerificationRequestId = null;
  bookingVerificationToken = null;
  renderBookingWizard();
}

// ==========================================================================
// STEP 2: DEMONSTRATION MOBILE OTP VERIFICATION
// ==========================================================================

function renderStep2DemonstrationOtp(container, it) {
  const phone = bookingPassengerData ? bookingPassengerData.phone : '+91 9876543210';
  const name = bookingPassengerData ? bookingPassengerData.full_name : 'Passenger';

  container.innerHTML = `
    ${renderWizardStepperHtml(2)}

    <div class="demo-otp-card">
      <div class="demo-sandbox-tag">
        <i class="fa-solid fa-flask"></i> DEMONSTRATION SANDBOX VERIFICATION
      </div>

      <h3 style="font-weight: 800; font-size: 1.35rem; margin-bottom: 0.35rem; color: #0f172a;">
        Verify Mobile Phone Number
      </h3>
      <p style="color: var(--text-muted); font-size: 0.85rem; line-height: 1.4; max-width: 440px; margin: 0 auto 1.25rem;">
        To ensure secure booking authorization, verify the contact mobile number for <strong>${name}</strong>.
        This is a demonstration sandbox flow — <strong>no real SMS was sent and no charges apply</strong>.
      </p>

      <div style="background: #f8fafc; border: 1px solid var(--border); border-radius: 8px; padding: 0.65rem 1rem; display: inline-flex; align-items: center; gap: 0.75rem; margin-bottom: 1.25rem;">
        <span style="font-size: 0.82rem; color: var(--text-muted);">Mobile:</span>
        <span style="font-weight: 800; font-size: 0.95rem; font-family: monospace; color: #1e293b;">${phone}</span>
        <button type="button" onclick="goToBookingStep1()" style="background: none; border: none; color: var(--primary); font-size: 0.78rem; font-weight: 700; cursor: pointer; text-decoration: underline; margin-left: 0.5rem;">
          Edit
        </button>
      </div>

      <!-- Demonstration OTP Interactive Banner -->
      <div id="demo-otp-banner-container">
        ${renderDemoOtpBannerHtml()}
      </div>

      <!-- 6-digit OTP Input -->
      <div style="margin: 1.25rem 0 0.5rem;">
        <label style="display: block; font-size: 0.82rem; font-weight: 700; color: #475569; margin-bottom: 0.5rem; text-transform: uppercase; letter-spacing: 0.5px;">
          Enter 6-Digit Demonstration Code
        </label>
        <input type="text" id="demo-otp-input" maxlength="6" placeholder="• • • • • •" 
               style="font-size: 1.85rem; font-family: monospace; letter-spacing: 10px; text-align: center; width: 230px; padding: 0.6rem 0.5rem; border: 2px solid var(--primary); border-radius: 10px; margin: 0 auto; display: block; outline: none; background: #ffffff;" 
               autocomplete="one-time-code" onkeyup="handleOtpKeyup(event)">
        <div id="otp-error-msg" style="color: #dc2626; font-size: 0.8rem; font-weight: 600; min-height: 22px; margin-top: 0.4rem;"></div>
      </div>

      <!-- Action Buttons -->
      <div style="display: flex; gap: 0.75rem; justify-content: center; margin-top: 1.25rem; flex-wrap: wrap;">
        <button class="btn-secondary" style="padding: 0.65rem 1.25rem; border-radius: 8px; font-weight: 700;" onclick="goToBookingStep1()">
          <i class="fa-solid fa-arrow-left"></i> Back to Passenger Info
        </button>
        <button id="btn-resend-otp" class="btn-outline" style="padding: 0.65rem 1.25rem; border-radius: 8px; font-weight: 700;" onclick="sendBookingOtp(true)">
          <i class="fa-solid fa-rotate-right"></i> Resend Demo OTP
        </button>
        <button id="btn-verify-otp" class="btn-search" style="padding: 0.65rem 1.5rem; border-radius: 8px; font-weight: 800;" onclick="verifyBookingOtp()">
          <i class="fa-solid fa-shield-check"></i> Verify OTP & Continue
        </button>
      </div>

      <div style="font-size: 0.72rem; color: #64748b; margin-top: 1rem; border-top: 1px dashed var(--border); padding-top: 0.75rem;">
        <i class="fa-solid fa-lock"></i> Verification token will be validated on the Flask backend before payment authorization.
      </div>
    </div>
  `;

  // Focus OTP input
  setTimeout(() => {
    const input = document.getElementById('demo-otp-input');
    if (input) input.focus();
  }, 100);
}

function renderDemoOtpBannerHtml() {
  if (isOtpSending) {
    return `
      <div style="background: #f1f5f9; border: 2px dashed #cbd5e1; border-radius: 10px; padding: 1rem; color: var(--text-muted); font-size: 0.88rem;">
        <i class="fa-solid fa-spinner fa-spin"></i> Generating secure demonstration OTP on backend...
      </div>
    `;
  }

  if (activeDemoOtp) {
    return `
      <div class="demo-otp-banner" onclick="autofillDemoOtp('${activeDemoOtp}')" title="Click to auto-fill demonstration OTP">
        <span style="font-size: 0.72rem; font-weight: 800; color: #1e40af; text-transform: uppercase; letter-spacing: 0.5px;">
          <i class="fa-solid fa-key"></i> DEMONSTRATION OTP CODE (CLICK TO AUTO-FILL)
        </span>
        <div class="demo-otp-digits">${activeDemoOtp}</div>
        <span style="font-size: 0.72rem; color: #475569;">
          <i class="fa-solid fa-mouse-pointer"></i> Click this box to auto-fill, or enter the 6 digits below
        </span>
      </div>
    `;
  }

  return `
    <div style="background: #eff6ff; border: 2px dashed #93c5fd; border-radius: 10px; padding: 0.85rem; cursor: pointer;" onclick="sendBookingOtp(false)">
      <button class="btn-search" style="padding: 0.5rem 1rem; font-size: 0.85rem;">
        <i class="fa-solid fa-paper-plane"></i> Click Here to Generate Demo OTP
      </button>
    </div>
  `;
}

/**
 * Calls Flask backend to generate a 6-digit demonstration OTP stored in session.
 */
async function sendBookingOtp(isResend = false) {
  if (isOtpSending || !bookingPassengerData) return;

  isOtpSending = true;
  const resendBtn = document.getElementById('btn-resend-otp');
  const bannerContainer = document.getElementById('demo-otp-banner-container');
  if (bannerContainer) bannerContainer.innerHTML = renderDemoOtpBannerHtml();
  if (resendBtn) {
    resendBtn.disabled = true;
    resendBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Sending...';
  }

  try {
    const res = await api.post('/bookings/otp/send', {
      phone: bookingPassengerData.phone,
      full_name: bookingPassengerData.full_name
    });

    if (res && res.status === 'success' && res.demo_otp) {
      activeDemoOtp = res.demo_otp;
      activeVerificationRequestId = res.request_id;
      bookingVerificationToken = null; // Reset any previous token
      showToast(`Demonstration OTP: ${res.demo_otp} (Sandbox Mode — No SMS sent)`, 'info');
    } else {
      throw new Error(res.message || 'Failed to generate demonstration OTP.');
    }
  } catch (err) {
    showToast(err.message || 'Error generating demonstration OTP.', 'danger');
  } finally {
    isOtpSending = false;
    if (bannerContainer) bannerContainer.innerHTML = renderDemoOtpBannerHtml();
    if (resendBtn) {
      resendBtn.disabled = false;
      resendBtn.innerHTML = '<i class="fa-solid fa-rotate-right"></i> Resend Demo OTP';
    }
  }
}

function autofillDemoOtp(code) {
  if (!activeDemoOtp || !activeVerificationRequestId) {
    showToast("No active OTP request found. Please click 'Send OTP' first.", "warning");
    return;
  }
  const input = document.getElementById('demo-otp-input');
  const errEl = document.getElementById('otp-error-msg');
  if (input) {
    input.value = code;
    input.focus();
  }
  if (errEl) errEl.textContent = '';
}

function handleOtpKeyup(event) {
  const input = event.target;
  input.value = input.value.replace(/\D/g, ''); // Numbers only
  const errEl = document.getElementById('otp-error-msg');
  if (errEl) errEl.textContent = '';

  if (event.key === 'Enter' && input.value.length === 6) {
    verifyBookingOtp();
  }
}

/**
 * Verifies submitted OTP against Flask backend session.
 */
async function verifyBookingOtp() {
  if (isOtpVerifying || !bookingPassengerData) return;

  const input = document.getElementById('demo-otp-input');
  const errEl = document.getElementById('otp-error-msg');
  const verifyBtn = document.getElementById('btn-verify-otp');
  const code = input ? input.value.trim() : '';

  if (!activeVerificationRequestId && !activeDemoOtp) {
    const errMsg = "No active OTP request found. Please click 'Send OTP' first.";
    if (errEl) errEl.textContent = errMsg;
    showToast(errMsg, 'warning');
    return;
  }

  if (!code || code.length !== 6) {
    if (errEl) errEl.textContent = 'Please enter the exact 6-digit demonstration OTP code.';
    if (input) input.focus();
    return;
  }

  isOtpVerifying = true;
  if (verifyBtn) {
    verifyBtn.disabled = true;
    verifyBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Verifying Code...';
  }
  if (errEl) errEl.textContent = '';

  try {
    const res = await api.post('/bookings/otp/verify', {
      request_id: activeVerificationRequestId,
      otp: code,
      phone: bookingPassengerData.phone
    });

    if (res && res.status === 'success' && res.verification_token) {
      bookingVerificationToken = res.verification_token;
      showToast('Mobile number verified successfully (Demonstration Sandbox)!', 'success');
      
      // Advance to Step 3: Summary & Payment
      bookingWizardStep = 3;
      renderBookingWizard();
    } else {
      throw new Error(res.message || 'OTP verification failed.');
    }
  } catch (err) {
    const msg = err.message || 'Invalid demonstration OTP. Please try again.';
    if (errEl) errEl.textContent = msg;
    showToast(msg, 'danger');
  } finally {
    isOtpVerifying = false;
    if (verifyBtn) {
      verifyBtn.disabled = false;
      verifyBtn.innerHTML = '<i class="fa-solid fa-shield-check"></i> Verify OTP & Continue';
    }
  }
}

// ==========================================================================
// STEP 3: BOOKING SUMMARY & DEMONSTRATION PAYMENT
// ==========================================================================

function renderStep3SummaryAndPayment(container, it) {
  const depTime = new Date(it.departure_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  const arrTime = new Date(it.arrival_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  // Compute pricing totals
  const baseFare = Number(it.base_fare);
  const taxesFees = Number(it.taxes + it.mandatory_fees);
  const seatCost = selectedSeat ? selectedSeat.cost : 0;
  
  let addonsCost = 0;
  const addonsSelected = [];
  if (bookingPassengerData && bookingPassengerData.addons) {
    if (bookingPassengerData.addons.meal) { addonsCost += 350; addonsSelected.push('Hot Gourmet Meal (+₹350)'); }
    if (bookingPassengerData.addons.insurance) { addonsCost += 199; addonsSelected.push('Comprehensive Insurance (+₹199)'); }
    if (bookingPassengerData.addons.priority) { addonsCost += 300; addonsSelected.push('Priority Baggage & Boarding (+₹300)'); }
  }
  const grandTotal = baseFare + taxesFees + seatCost + addonsCost;

  container.innerHTML = `
    ${renderWizardStepperHtml(3)}

    <div style="border-bottom: 1px solid var(--border); padding-bottom: 0.75rem; margin-bottom: 1.25rem;">
      <h3 style="font-weight: 800; margin-bottom: 0.25rem;">Step 3: Review Booking Summary & Complete Demonstration Payment</h3>
      <p style="color: var(--text-muted); font-size: 0.88rem;">
        Mobile verified for <strong>${bookingPassengerData ? bookingPassengerData.phone : ''}</strong>. Select your simulated payment method to finalize the reservation.
      </p>
    </div>

    <div style="display: grid; grid-template-columns: 1.25fr 1fr; gap: 1.75rem;">
      <!-- Left Column: Payment Method Picker & Demonstration Fields -->
      <div>
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
          <h4 style="font-weight: 700;"><i class="fa-solid fa-credit-card" style="color: var(--primary);"></i> Select Payment Method</h4>
          <span class="demo-sandbox-tag" style="margin-bottom: 0;">
            <i class="fa-solid fa-flask"></i> DEMO GATEWAY
          </span>
        </div>

        <p style="font-size: 0.78rem; color: var(--text-muted); margin-bottom: 0.85rem;">
          Choose any demonstration payment method below. No actual financial transaction will be conducted.
        </p>

        <!-- 4 Payment Methods Grid -->
        <div class="payment-methods-grid">
          <div class="payment-method-card ${selectedPaymentMode === 'card' ? 'selected' : ''}" onclick="selectPaymentMethod('card')">
            <div class="payment-card-icon"><i class="fa-regular fa-credit-card"></i></div>
            <div>
              <div class="payment-card-title">Credit / Debit Card</div>
              <div class="payment-card-sub">Visa / Mastercard / RuPay Demo</div>
            </div>
          </div>

          <div class="payment-method-card ${selectedPaymentMode === 'upi' ? 'selected' : ''}" onclick="selectPaymentMethod('upi')">
            <div class="payment-card-icon"><i class="fa-solid fa-mobile-screen"></i></div>
            <div>
              <div class="payment-card-title">UPI Demonstration</div>
              <div class="payment-card-sub">GPay / PhonePe / Paytm / VPA</div>
            </div>
          </div>

          <div class="payment-method-card ${selectedPaymentMode === 'qr' ? 'selected' : ''}" onclick="selectPaymentMethod('qr')">
            <div class="payment-card-icon"><i class="fa-solid fa-qrcode"></i></div>
            <div>
              <div class="payment-card-title">Dynamic QR Code</div>
              <div class="payment-card-sub">Simulated Bharat QR Scan</div>
            </div>
          </div>

          <div class="payment-method-card ${selectedPaymentMode === 'netbanking' ? 'selected' : ''}" onclick="selectPaymentMethod('netbanking')">
            <div class="payment-card-icon"><i class="fa-solid fa-building-columns"></i></div>
            <div>
              <div class="payment-card-title">Net Banking Demo</div>
              <div class="payment-card-sub">SBI / HDFC / ICICI / Axis</div>
            </div>
          </div>
        </div>

        <!-- Dynamic Payment Method Details -->
        <div id="payment-details-form" style="background: #f8fafc; border: 1px solid var(--border); border-radius: 10px; padding: 1.15rem; margin-bottom: 1.25rem;">
          ${renderPaymentDetailsForm(grandTotal)}
        </div>

        <!-- Demonstration Notice Banner -->
        <div style="background: #fffbeb; border: 1px solid #fef3c7; border-radius: 8px; padding: 0.75rem 0.9rem; font-size: 0.74rem; color: #92400e; line-height: 1.4;">
          <i class="fa-solid fa-circle-info" style="color: #d97706;"></i>
          <strong>Demonstration Sandbox Notice:</strong> No real money will be charged or transferred. All payment authorizations, references, and ticket numbers are electronically simulated and recorded in MySQL for educational demonstration.
        </div>
      </div>

      <!-- Right Column: Verified Itinerary Summary & Payment Authorization -->
      <div style="background: #ffffff; border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 1.25rem; display: flex; flex-direction: column; justify-content: space-between;">
        <div>
          <h4 style="font-weight: 700; margin-bottom: 0.85rem; border-bottom: 1px solid var(--border); padding-bottom: 0.5rem; display: flex; justify-content: space-between; align-items: center;">
            <span>Booking Summary</span>
            <span style="font-size: 0.72rem; color: #059669; font-weight: 800; background: #ecfdf5; padding: 2px 8px; border-radius: 4px; border: 1px solid #a7f3d0;">
              <i class="fa-solid fa-check"></i> OTP VERIFIED
            </span>
          </h4>

          <!-- Flight Details -->
          <div style="margin-bottom: 0.85rem; font-size: 0.85rem;">
            <div style="font-weight: 800; color: #0f172a;">${it.airline_name} (${it.segments[0].flight_number})</div>
            <div style="color: var(--text-muted); font-size: 0.78rem;">
              ${it.origin_city} (${it.origin_code}) → ${it.destination_city} (${it.destination_code}) • ${depTime} - ${arrTime}
            </div>
          </div>

          <!-- Passenger Details -->
          <div style="background: #f8fafc; border: 1px solid var(--border); border-radius: 8px; padding: 0.65rem 0.85rem; margin-bottom: 0.85rem; font-size: 0.8rem;">
            <div style="display: flex; justify-content: space-between;">
              <span style="color: var(--text-muted);">Passenger:</span>
              <strong>${bookingPassengerData ? bookingPassengerData.full_name : ''}</strong>
            </div>
            <div style="display: flex; justify-content: space-between; margin-top: 0.25rem;">
              <span style="color: var(--text-muted);">Verified Mobile:</span>
              <span style="font-family: monospace; font-weight: 700; color: #059669;">${bookingPassengerData ? bookingPassengerData.phone : ''}</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-top: 0.25rem;">
              <span style="color: var(--text-muted);">Selected Seat:</span>
              <span style="font-weight: 700; color: var(--primary);">${selectedSeat ? selectedSeat.seat_number : 'Auto-Assigned'}</span>
            </div>
          </div>

          <!-- Selected Add-ons -->
          ${addonsSelected.length > 0 ? `
            <div style="font-size: 0.75rem; color: #475569; margin-bottom: 0.85rem;">
              <strong>Add-ons Included:</strong>
              <ul style="margin: 0.25rem 0 0 1.25rem; padding: 0;">
                ${addonsSelected.map(a => `<li>${a}</li>`).join('')}
              </ul>
            </div>
          ` : ''}

          <!-- Fare Breakdown -->
          <div style="border-top: 1px solid var(--border); padding-top: 0.65rem; font-size: 0.82rem;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 0.3rem;">
              <span style="color: var(--text-muted);">Base Airfare</span>
              <span>₹${baseFare.toLocaleString('en-IN')}</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 0.3rem;">
              <span style="color: var(--text-muted);">Taxes & Fees</span>
              <span>₹${taxesFees.toLocaleString('en-IN')}</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 0.3rem;">
              <span style="color: var(--text-muted);">Seat Fee</span>
              <span>₹${seatCost.toLocaleString('en-IN')}</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
              <span style="color: var(--text-muted);">Add-ons Fee</span>
              <span>₹${addonsCost.toLocaleString('en-IN')}</span>
            </div>
            <div style="display: flex; justify-content: space-between; font-size: 1.2rem; font-weight: 800; border-top: 2px dashed var(--border); padding-top: 0.6rem; color: var(--primary);">
              <span>Total Payable</span>
              <span>₹${grandTotal.toLocaleString('en-IN')}</span>
            </div>
          </div>
        </div>

        <!-- Buttons -->
        <div style="margin-top: 1.25rem; display: flex; flex-direction: column; gap: 0.5rem;">
          <button id="btn-proceed-payment" class="btn-search" style="width: 100%; height: 50px; font-size: 0.96rem; font-weight: 800;" onclick="processDemonstrationPayment()">
            <i class="fa-solid fa-lock"></i> Proceed to Payment (₹${grandTotal.toLocaleString('en-IN')})
          </button>
          <button class="btn-secondary" style="width: 100%; padding: 0.55rem; font-size: 0.82rem; font-weight: 600;" onclick="goToBookingStep2()">
            <i class="fa-solid fa-arrow-left"></i> Back to OTP Verification
          </button>
        </div>
      </div>
    </div>
  `;
}

function selectPaymentMethod(mode) {
  selectedPaymentMode = mode;
  document.querySelectorAll('.payment-method-card').forEach(el => el.classList.remove('selected'));
  
  // Update form view
  const formContainer = document.getElementById('payment-details-form');
  if (!activeBookingItinerary) return;

  const baseFare = Number(activeBookingItinerary.base_fare);
  const taxesFees = Number(activeBookingItinerary.taxes + activeBookingItinerary.mandatory_fees);
  const seatCost = selectedSeat ? selectedSeat.cost : 0;
  let addonsCost = 0;
  if (bookingPassengerData && bookingPassengerData.addons) {
    if (bookingPassengerData.addons.meal) addonsCost += 350;
    if (bookingPassengerData.addons.insurance) addonsCost += 199;
    if (bookingPassengerData.addons.priority) addonsCost += 300;
  }
  const grandTotal = baseFare + taxesFees + seatCost + addonsCost;

  if (formContainer) {
    formContainer.innerHTML = renderPaymentDetailsForm(grandTotal);
  }

  // Highlight selected card
  document.querySelectorAll('.payment-method-card').forEach(card => {
    if (card.getAttribute('onclick')?.includes(mode)) {
      card.classList.add('selected');
    }
  });
}

function renderPaymentDetailsForm(grandTotal) {
  const pName = bookingPassengerData ? bookingPassengerData.full_name : 'Passenger';

  if (selectedPaymentMode === 'card') {
    return `
      <div style="font-size: 0.8rem; font-weight: 700; color: #1e293b; margin-bottom: 0.65rem;">
        <i class="fa-regular fa-credit-card" style="color: var(--primary);"></i> Demonstration Card Information
      </div>
      <div class="form-group" style="margin-bottom: 0.65rem;">
        <label style="font-size: 0.74rem;">Card Number (Demonstration Sandbox)</label>
        <input type="text" value="4532 •••• •••• 8820" readonly style="padding: 0.55rem; border: 1px solid var(--border); border-radius: 6px; width: 100%; font-family: monospace; font-weight: 700; background: #ffffff;">
      </div>
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.65rem; margin-bottom: 0.65rem;">
        <div class="form-group">
          <label style="font-size: 0.74rem;">Valid Thru</label>
          <input type="text" value="12 / 29" readonly style="padding: 0.55rem; border: 1px solid var(--border); border-radius: 6px; width: 100%; font-family: monospace; font-weight: 700; background: #ffffff;">
        </div>
        <div class="form-group">
          <label style="font-size: 0.74rem;">CVV</label>
          <input type="password" value="888" readonly style="padding: 0.55rem; border: 1px solid var(--border); border-radius: 6px; width: 100%; font-family: monospace; font-weight: 700; background: #ffffff;">
        </div>
      </div>
      <div class="form-group">
        <label style="font-size: 0.74rem;">Name on Card</label>
        <input type="text" value="${pName}" readonly style="padding: 0.55rem; border: 1px solid var(--border); border-radius: 6px; width: 100%; font-weight: 600; background: #ffffff;">
      </div>
    `;
  }

  if (selectedPaymentMode === 'upi') {
    return `
      <div style="font-size: 0.8rem; font-weight: 700; color: #1e293b; margin-bottom: 0.65rem;">
        <i class="fa-solid fa-mobile-screen" style="color: var(--primary);"></i> Demonstration UPI Virtual Payment Address (VPA)
      </div>
      <div class="form-group" style="margin-bottom: 0.75rem;">
        <label style="font-size: 0.74rem;">UPI ID / VPA</label>
        <input type="text" id="demo-upi-id" value="traveler@okhdfcbank" style="padding: 0.55rem; border: 1px solid var(--border); border-radius: 6px; width: 100%; font-family: monospace; font-weight: 700; background: #ffffff;">
      </div>
      <div style="font-size: 0.72rem; color: var(--text-muted); margin-bottom: 0.4rem;">Quick Sandbox Handles:</div>
      <div style="display: flex; gap: 0.4rem; flex-wrap: wrap;">
        <button type="button" class="btn-demo-creds" onclick="document.getElementById('demo-upi-id').value='traveler@okhdfcbank'">traveler@okhdfcbank</button>
        <button type="button" class="btn-demo-creds" onclick="document.getElementById('demo-upi-id').value='flywise.user@okaxis'">flywise.user@okaxis</button>
        <button type="button" class="btn-demo-creds" onclick="document.getElementById('demo-upi-id').value='paytm.user@paytm'">paytm.user@paytm</button>
      </div>
    `;
  }

  if (selectedPaymentMode === 'qr') {
    const qrSvg = generateQrSvg(`FLYWISE:SIM-PAY:INR:${grandTotal}:${Date.now()}`);
    return `
      <div style="font-size: 0.8rem; font-weight: 700; color: #1e293b; margin-bottom: 0.5rem; text-align: center;">
        <i class="fa-solid fa-qrcode" style="color: var(--primary);"></i> Scan & Pay Bharat QR (Demonstration)
      </div>
      <div style="display: flex; flex-direction: column; align-items: center; gap: 0.5rem; margin: 0.5rem 0;">
        <div style="padding: 0.65rem; background: white; border: 1px solid var(--border); border-radius: 8px; box-shadow: 0 2px 6px rgba(0,0,0,0.05);">
          ${qrSvg}
        </div>
        <div style="font-size: 0.74rem; font-weight: 700; color: var(--primary);">
          Pay ₹${grandTotal.toLocaleString('en-IN')} via any UPI App
        </div>
        <div style="font-size: 0.7rem; color: var(--text-muted);">
          Simulated Dynamic QR Code • Click "Proceed to Payment" to authorize
        </div>
      </div>
    `;
  }

  if (selectedPaymentMode === 'netbanking') {
    return `
      <div style="font-size: 0.8rem; font-weight: 700; color: #1e293b; margin-bottom: 0.65rem;">
        <i class="fa-solid fa-building-columns" style="color: var(--primary);"></i> Select Demonstration Bank
      </div>
      <div class="form-group" style="margin-bottom: 0.75rem;">
        <label style="font-size: 0.74rem;">Popular Demonstration Banks</label>
        <select id="demo-bank-select" style="padding: 0.55rem; border: 1px solid var(--border); border-radius: 6px; width: 100%; font-weight: 600; background: #ffffff;">
          <option value="HDFC">HDFC Bank (Demonstration)</option>
          <option value="SBI">State Bank of India (Demonstration)</option>
          <option value="ICICI">ICICI Bank (Demonstration)</option>
          <option value="AXIS">Axis Bank (Demonstration)</option>
          <option value="KOTAK">Kotak Mahindra Bank (Demonstration)</option>
        </select>
      </div>
      <div style="font-size: 0.72rem; color: var(--text-muted);">
        Fast simulated redirect with instant MySQL confirmation.
      </div>
    `;
  }

  return '';
}

// ==========================================================================
// STEP 4: PAYMENT EXECUTION, BACKEND CONFIRMATION & TICKET GENERATION
// ==========================================================================

/**
 * Executes the payment and booking transaction.
 * Enforces that OTP has been verified and prevents duplicate submissions.
 */
async function processDemonstrationPayment() {
  if (isBookingSubmitting) return;

  const user = api.getUser();
  if (!user) {
    showToast('Please sign in to your FlyWise account.', 'warning');
    openAuthModal('login');
    return;
  }

  if (!bookingVerificationToken) {
    showToast('Mobile OTP verification is required before proceeding to payment.', 'danger');
    goToBookingStep2();
    return;
  }

  if (!activeBookingItinerary || !activeBookingItinerary.segments || activeBookingItinerary.segments.length === 0) {
    showToast('Invalid flight itinerary. Please search again.', 'danger');
    return;
  }

  if (!bookingPassengerData) {
    showToast('Passenger details are missing. Please complete Step 1.', 'danger');
    goToBookingStep1();
    return;
  }

  const submitBtn = document.getElementById('btn-proceed-payment');

  // Recalculate total
  const baseTotal = activeBookingItinerary.total_fare;
  const seatCost = selectedSeat ? selectedSeat.cost : 0;
  let addonsCost = 0;
  if (bookingPassengerData.addons) {
    if (bookingPassengerData.addons.meal) addonsCost += 350;
    if (bookingPassengerData.addons.insurance) addonsCost += 199;
    if (bookingPassengerData.addons.priority) addonsCost += 300;
  }
  const grandTotal = baseTotal + seatCost + addonsCost;

  const payload = {
    itinerary_id: activeBookingItinerary.itinerary_id,
    flight_ids: activeBookingItinerary.segments.map(s => s.flight_id),
    passengers: [{
      full_name: bookingPassengerData.full_name,
      email: bookingPassengerData.email,
      phone: bookingPassengerData.phone,
      gender: bookingPassengerData.gender,
      date_of_birth: bookingPassengerData.date_of_birth,
      passenger_type: 'Adult'
    }],
    seat_assignments: selectedSeat ? [{ seat_id: selectedSeat.seat_id }] : [],
    add_ons: bookingPassengerData.addons,
    total_amount: grandTotal,
    payment_mode: selectedPaymentMode,
    verification_token: bookingVerificationToken
  };

  // Prevent duplicate submissions & show clear loading state
  isBookingSubmitting = true;
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Authorizing Demonstration Payment & Reserving in MySQL...';
  }

  try {
    const res = await api.post('/bookings', payload);

    // Backend must confirm success and return the verified booking record from MySQL
    if (res && res.status === 'success' && res.booking) {
      closeModal('booking-modal');
      
      // Invalidate local verification token to prevent replay
      bookingVerificationToken = null;
      activeDemoOtp = null;

      // Show official airline-style ticket confirmation
      showBookingConfirmation(res.booking);
      showToast('Booking confirmed & digital e-ticket issued successfully!', 'success');
    } else {
      throw new Error((res && res.message) ? res.message : 'Booking transaction could not be confirmed by the server.');
    }
  } catch (err) {
    showToast(err.message || 'Payment transaction failed. No booking was created.', 'danger');
  } finally {
    isBookingSubmitting = false;
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.innerHTML = `<i class="fa-solid fa-lock"></i> Proceed to Payment (₹${grandTotal.toLocaleString('en-IN')})`;
    }
  }
}

// ==========================================================================
// TICKET GENERATION & 1-PAGE A4 PRINT RENDERING
// ==========================================================================

function generateQrSvg(dataText) {
  let hash = 0;
  for (let i = 0; i < dataText.length; i++) {
    hash = ((hash << 5) - hash) + dataText.charCodeAt(i);
    hash |= 0;
  }

  const size = 25;
  let cells = '';
  const drawRect = (x, y, w = 1, h = 1) => `<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="#0f172a" />`;

  // 3 Corner finder patterns
  cells += drawRect(0, 0, 7, 1) + drawRect(0, 6, 7, 1) + drawRect(0, 1, 1, 5) + drawRect(6, 1, 1, 5) + drawRect(2, 2, 3, 3);
  cells += drawRect(18, 0, 7, 1) + drawRect(18, 6, 7, 1) + drawRect(18, 1, 1, 5) + drawRect(24, 1, 1, 5) + drawRect(20, 2, 3, 3);
  cells += drawRect(0, 18, 7, 1) + drawRect(0, 24, 7, 1) + drawRect(0, 19, 1, 5) + drawRect(6, 19, 1, 5) + drawRect(2, 20, 3, 3);

  // Timing patterns
  for (let i = 8; i < 17; i += 2) {
    cells += drawRect(i, 6, 1, 1) + drawRect(6, i, 1, 1);
  }

  // Data modules
  let bitIdx = 0;
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      if ((x <= 7 && y <= 7) || (x >= 17 && y <= 7) || (x <= 7 && y >= 17)) continue;
      if (x === 6 || y === 6) continue;

      const pseudo = (Math.sin(hash + (x * 31) + (y * 17) + bitIdx) * 10000);
      if ((pseudo - Math.floor(pseudo)) > 0.45) {
        cells += drawRect(x, y, 1, 1);
      }
      bitIdx++;
    }
  }

  return `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${size} ${size}" width="60" height="60" style="display: block; shape-rendering: crispEdges;">
      <rect width="${size}" height="${size}" fill="#ffffff" />
      ${cells}
    </svg>
  `;
}

function generateAirlineTicketHtml(booking) {
  const p = (booking.passengers && booking.passengers[0]) ? booking.passengers[0] : { full_name: 'Valued Passenger', ticket_number: 'PENDING' };
  const seg = (booking.segments && booking.segments[0]) ? booking.segments[0] : {};

  // Formatted Dates & Times
  const bookingDate = booking.confirmed_at || booking.created_at || new Date().toISOString();
  const bookingDateStr = new Date(bookingDate).toLocaleString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit'
  });

  const depDate = seg.scheduled_departure ? new Date(seg.scheduled_departure) : null;
  const arrDate = seg.scheduled_arrival ? new Date(seg.scheduled_arrival) : null;

  const depDateStr = depDate ? depDate.toLocaleDateString('en-IN', { weekday: 'short', day: '2-digit', month: 'short', year: 'numeric' }) : 'N/A';
  const depTimeStr = depDate ? depDate.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' }) : 'N/A';

  const arrDateStr = arrDate ? arrDate.toLocaleDateString('en-IN', { weekday: 'short', day: '2-digit', month: 'short', year: 'numeric' }) : 'N/A';
  const arrTimeStr = arrDate ? arrDate.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' }) : 'N/A';

  let durationStr = 'Direct';
  if (seg.duration_minutes) {
    const hrs = Math.floor(seg.duration_minutes / 60);
    const mins = seg.duration_minutes % 60;
    durationStr = `${hrs}h ${mins}m`;
  } else if (depDate && arrDate) {
    const diffMs = arrDate - depDate;
    const diffMins = Math.floor(diffMs / 60000);
    const hrs = Math.floor(diffMins / 60);
    const mins = diffMins % 60;
    durationStr = `${hrs}h ${mins}m`;
  }

  const airlineName = seg.airline_name || 'Operating Airline';
  const flightNumber = seg.flight_number || 'N/A';
  const cabinClass = (seg.travel_class || 'Economy').toUpperCase();
  const originCode = seg.origin_code || 'ORIG';
  const originCity = seg.origin_city || originCode;
  const originAirport = seg.origin_name || `${originCity} Airport`;

  const destCode = seg.destination_code || 'DEST';
  const destCity = seg.destination_city || destCode;
  const destAirport = seg.destination_name || `${destCity} Airport`;

  // Assigned seat and ticket
  const seatNumber = p.seat_number || (selectedSeat ? selectedSeat.seat_number : 'Auto-Assigned at Check-in');
  const ticketNumber = p.ticket_number || `TK-${seg.airline_code || '6E'}-${booking.booking_id || '001'}`;

  // Add-ons summary
  let addonsList = [];
  if (Array.isArray(p.addons) && p.addons.length > 0) {
    addonsList = p.addons;
  } else if (bookingPassengerData && bookingPassengerData.addons) {
    if (bookingPassengerData.addons.meal) addonsList.push('Hot Gourmet Meal');
    if (bookingPassengerData.addons.insurance) addonsList.push('Travel Insurance');
    if (bookingPassengerData.addons.priority) addonsList.push('Priority Baggage');
  }
  const addonsSummary = addonsList.length > 0 ? addonsList.join(' • ') : 'Standard Baggage (15kg Check-in, 7kg Cabin)';

  // Fare Breakdown
  const fb = booking.fare_breakdown || {};
  const totalAmount = Number(booking.total_amount || 0);
  const baseFare = Number(fb.base_fare || Math.round(totalAmount * 0.78));
  const taxesFees = Number(fb.taxes_and_fees || Math.round(totalAmount * 0.18));
  const seatFee = Number(fb.seat_fee || (selectedSeat ? selectedSeat.cost : 0));
  const addonsFee = Number(fb.addons_fee || Math.max(0, totalAmount - baseFare - taxesFees - seatFee));
  
  // Payment Mode label
  const paymentRef = booking.provider_reference || booking.payment_reference || 'SIM-PAY-CARD';
  let paymentModeLabel = 'Credit/Debit Card (Demonstration)';
  if (paymentRef.includes('UPI')) paymentModeLabel = 'UPI Instant (Demonstration)';
  else if (paymentRef.includes('QR')) paymentModeLabel = 'Dynamic Bharat QR (Demonstration)';
  else if (paymentRef.includes('NETBANKING') || paymentRef.includes('NET_BANKING')) paymentModeLabel = 'Net Banking (Demonstration)';
  else if (paymentRef.includes('CARD')) paymentModeLabel = 'Credit/Debit Card (Demonstration)';

  const qrSvg = generateQrSvg(`PNR:${booking.booking_reference}|NAME:${p.full_name}|FLIGHT:${flightNumber}`);

  return `
    <div id="flywise-digital-ticket" class="airline-ticket-wrapper">
      <!-- 1. Header Section -->
      <div class="ticket-header-row">
        <div class="ticket-logo-block">
          <div class="ticket-brand-title">
            <i class="fa-solid fa-plane-up"></i>
            <span>FlyWise</span>
          </div>
          <div class="ticket-doc-type">Electronic Ticket & Travel Itinerary Receipt</div>
        </div>

        <div class="ticket-pnr-block">
          <div class="ticket-pnr-tag">BOOKING REFERENCE (PNR)</div>
          <div class="ticket-pnr-code">${booking.booking_reference}</div>
          <div class="ticket-meta-tags">
            <span class="ticket-status-pill"><i class="fa-solid fa-check"></i> CONFIRMED</span>
            <span style="color: #64748b; font-weight: 600;">${bookingDateStr}</span>
          </div>
        </div>
      </div>

      <!-- Demonstration Notice Banner -->
      <div class="ticket-simulated-banner">
        <span class="ticket-simulated-badge">
          <i class="fa-solid fa-circle-check"></i> DEMONSTRATION PAYMENT — CONFIRMED & VERIFIED IN MYSQL
        </span>
        <span>Sandbox Mode • Ref: <code>${paymentRef}</code></span>
      </div>

      <!-- 2. Flight Details (IndiGo Style) -->
      <div class="ticket-flight-card">
        <div class="ticket-flight-info-row">
          <div>
            <span class="ticket-airline-name">${airlineName}</span>
            <span class="ticket-flight-number">${flightNumber}</span>
          </div>
          <div style="color: #475569; font-size: 0.76rem;">
            Class: <strong>${cabinClass}</strong> • Duration: <strong>${durationStr}</strong> • Status: <strong style="color: #059669;">Confirmed</strong>
          </div>
        </div>

        <div class="ticket-route-grid">
          <!-- Origin -->
          <div class="ticket-route-node left">
            <div class="ticket-iata">${originCode}</div>
            <div class="ticket-city">${originCity}</div>
            <div class="ticket-airport">${originAirport}</div>
            <div class="ticket-datetime">${depTimeStr}</div>
            <div class="ticket-subdate">${depDateStr}</div>
          </div>

          <!-- Middle Flight Visualization -->
          <div class="ticket-route-center">
            <span class="ticket-flight-mode">NON-STOP</span>
            <div class="ticket-flight-line">
              <span class="dot"></span>
              <span class="line"></span>
              <i class="fa-solid fa-plane plane-icon"></i>
              <span class="line"></span>
              <span class="dot"></span>
            </div>
            <span class="ticket-duration-label">${durationStr}</span>
          </div>

          <!-- Destination -->
          <div class="ticket-route-node right">
            <div class="ticket-iata">${destCode}</div>
            <div class="ticket-city">${destCity}</div>
            <div class="ticket-airport">${destAirport}</div>
            <div class="ticket-datetime">${arrTimeStr}</div>
            <div class="ticket-subdate">${arrDateStr}</div>
          </div>
        </div>
      </div>

      <!-- 3. Passenger Information Table -->
      <div class="ticket-section-title">PASSENGER & SEAT INFORMATION</div>
      <table class="ticket-passengers-table">
        <thead>
          <tr>
            <th style="width: 28%;">PASSENGER NAME</th>
            <th style="width: 12%;">TYPE</th>
            <th style="width: 15%;">SEAT</th>
            <th style="width: 20%;">E-TICKET NUMBER</th>
            <th style="width: 25%;">SERVICES & ADD-ONS</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><strong>${p.full_name}</strong></td>
            <td>${p.passenger_type || 'Adult'}</td>
            <td><span class="ticket-seat-pill">${seatNumber}</span></td>
            <td><code>${ticketNumber}</code></td>
            <td style="font-size: 0.72rem; color: #475569;">${addonsSummary}</td>
          </tr>
        </tbody>
      </table>

      <!-- 4. Fare Summary & Payment Breakdown -->
      <div class="ticket-section-title">FARE SUMMARY & PAYMENT BREAKDOWN</div>
      <div class="ticket-fare-box">
        <div class="ticket-fare-left">
          <div class="ticket-fare-line">
            <span style="color: #64748b;">Base Airfare:</span>
            <span>₹${baseFare.toLocaleString('en-IN')}</span>
          </div>
          <div class="ticket-fare-line">
            <span style="color: #64748b;">Seat Selection Fee:</span>
            <span>₹${seatFee.toLocaleString('en-IN')}</span>
          </div>
          <div class="ticket-fare-line">
            <span style="color: #64748b;">Taxes & Airline Fees:</span>
            <span>₹${taxesFees.toLocaleString('en-IN')}</span>
          </div>
          <div class="ticket-fare-line">
            <span style="color: #64748b;">Journey Add-ons:</span>
            <span>₹${addonsFee.toLocaleString('en-IN')}</span>
          </div>
        </div>

        <div class="ticket-fare-right">
          <div style="font-size: 0.68rem; font-weight: 700; color: #64748b; text-transform: uppercase;">Total Amount Paid</div>
          <div class="ticket-fare-grand-total">₹${totalAmount.toLocaleString('en-IN')}</div>
          <div style="font-size: 0.66rem; color: #059669; font-weight: 700; margin-top: 2px;">
            <i class="fa-solid fa-circle-check"></i> Paid via ${paymentModeLabel}
          </div>
        </div>
      </div>

      <!-- 5. Important Travel Guidelines -->
      <div class="ticket-guidelines-box">
        <div><strong>• Photo Identification:</strong> A valid government-issued photo ID (Aadhaar, Passport, Voter ID) is mandatory at airport security and boarding gates.</div>
        <div><strong>• Airport Reporting:</strong> Web check-in opens 48 hours prior to scheduled departure. Airport check-in counters close 60 mins before departure; boarding gates close 25 mins prior.</div>
        <div><strong>• Baggage Policy:</strong> Standard hand baggage allowance is 7 kg (1 piece); check-in baggage allowance is 15 kg per passenger. Please verify applicable airline limits for excess baggage.</div>
      </div>

      <!-- 6. Footer & Verification -->
      <div class="ticket-footer-row">
        <div class="ticket-footer-text">
          <strong style="color: #0f172a;">FlyWise Intelligent Travel & Journey Management System</strong><br>
          This is an electronically generated travel document verified against live MySQL records. No real financial transaction was conducted (Educational & Demonstration System).
          Please monitor airport display screens for real-time gate and boarding announcements.
        </div>
        <div class="ticket-footer-qr">
          ${qrSvg}
          <div class="ticket-qr-caption">PNR: ${booking.booking_reference}</div>
        </div>
      </div>
    </div>

    <!-- Modal Action Buttons (Screen Only) -->
    <div class="ticket-modal-actions">
      <button class="btn-search" style="padding: 0.65rem 1.25rem;" onclick="printTicketDocument()">
        <i class="fa-solid fa-print"></i> Print Ticket (1 Page A4)
      </button>
      <button style="background: #f1f5f9; border: 1px solid #cbd5e1; padding: 0.65rem 1.25rem; border-radius: 8px; font-weight: 700; cursor: pointer;" onclick="closeModal('ticket-modal'); navigateToJourneys();">
        <i class="fa-solid fa-compass"></i> View in Journey Dashboard
      </button>
      <button style="background: white; border: 1px solid #cbd5e1; padding: 0.65rem 1rem; border-radius: 8px; font-weight: 700; cursor: pointer;" onclick="closeModal('ticket-modal')">
        Close
      </button>
    </div>
  `;
}

function showBookingConfirmation(booking) {
  const modal = document.getElementById('ticket-modal');
  const body = document.getElementById('ticket-modal-body');
  if (!modal || !body) return;

  body.innerHTML = generateAirlineTicketHtml(booking);
  openModal('ticket-modal');
}

function printTicketDocument() {
  const ticket = document.getElementById('flywise-digital-ticket');
  if (!ticket) {
    showToast('Ticket content is not ready to print.', 'warning');
    return;
  }
  window.print();
}

async function openTicketModalForBooking(bookingRef) {
  try {
    const data = await api.get(`/bookings/${bookingRef}`);
    if (data && data.booking) {
      showBookingConfirmation(data.booking);
    } else {
      showToast('Booking details could not be retrieved.', 'danger');
    }
  } catch (err) {
    showToast(err.message || 'Error loading booking ticket.', 'danger');
  }
}
