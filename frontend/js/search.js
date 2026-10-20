/**
 * FlyWise AI - Flight Search & Comparison Module
 */

let currentSearchResults = [];
let selectedForCompare = [];
let isSearchingFlights = false;
let lastSearchCriteria = {
  origin: 'TIR',
  destination: 'DEL',
  date: '2026-10-23',
  returnDate: '2026-10-26',
  tripType: 'oneway',
  passengers: 1,
  travelClass: 'economy'
};

function toggleTripType(type) {
  const returnGroup = document.getElementById('search-return-date-group');
  const returnInput = document.getElementById('search-return-date');
  const depInput = document.getElementById('search-date');
  if (!returnGroup) return;

  if (type === 'roundtrip') {
    returnGroup.style.display = 'flex';
    if (returnInput && depInput && depInput.value) {
      const depDate = new Date(depInput.value);
      if (!isNaN(depDate.getTime())) {
        depDate.setDate(depDate.getDate() + 3);
        const yyyy = depDate.getFullYear();
        const mm = String(depDate.getMonth() + 1).padStart(2, '0');
        const dd = String(depDate.getDate()).padStart(2, '0');
        returnInput.value = `${yyyy}-${mm}-${dd}`;
        returnInput.min = depInput.value;
      }
    }
  } else {
    returnGroup.style.display = 'none';
  }
}
window.toggleTripType = toggleTripType;

function showSearchValidationError(message, fieldElement) {
  const msgContainer = document.getElementById('search-validation-msg');
  const msgText = document.getElementById('search-validation-msg-text');
  if (msgContainer && msgText) {
    msgText.textContent = message;
    msgContainer.style.display = 'flex';
  }
  showToast(message, 'warning');
  if (fieldElement) {
    fieldElement.style.borderColor = 'var(--danger)';
    fieldElement.focus();
  }
}

function clearSearchValidationError() {
  const msgContainer = document.getElementById('search-validation-msg');
  if (msgContainer) {
    msgContainer.style.display = 'none';
  }
  ['search-origin', 'search-destination', 'search-date', 'search-return-date', 'search-passengers'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.style.borderColor = '';
  });
}

async function performFlightSearch(e) {
  if (e && e.preventDefault) e.preventDefault();
  if (isSearchingFlights) return;

  clearSearchValidationError();

  const originEl = document.getElementById('search-origin');
  const destEl = document.getElementById('search-destination');
  const dateEl = document.getElementById('search-date');
  const returnDateEl = document.getElementById('search-return-date');
  const passengersEl = document.getElementById('search-passengers');
  const classEl = document.getElementById('search-class');
  const sortByEl = document.getElementById('sort-by-select');
  const tripTypeEl = document.querySelector('input[name="trip_type"]:checked');

  const origin = originEl ? originEl.value.trim().toUpperCase() : '';
  const destination = destEl ? destEl.value.trim().toUpperCase() : '';
  const date = dateEl ? dateEl.value.trim() : '';
  const tripType = tripTypeEl ? tripTypeEl.value : 'oneway';
  const returnDate = returnDateEl ? returnDateEl.value.trim() : '';
  const passengers = passengersEl ? parseInt(passengersEl.value, 10) : 1;
  const travelClass = classEl ? classEl.value : 'economy';
  const sortBy = sortByEl ? sortByEl.value : 'recommendation';

  // 1. Validate departure city
  if (!origin) {
    showSearchValidationError('Please select a departure city (Origin Airport).', originEl);
    return;
  }

  // 2. Validate destination city
  if (!destination) {
    showSearchValidationError('Please select a destination city (Destination Airport).', destEl);
    return;
  }

  // 3. Ensure departure and destination cannot be the same
  if (origin === destination) {
    showSearchValidationError('Departure and destination cannot be the same city. Please select different airports.', destEl);
    if (originEl) originEl.style.borderColor = 'var(--danger)';
    return;
  }

  // 4. Validate departure date
  if (!date) {
    showSearchValidationError('Please select a departure date.', dateEl);
    return;
  }
  const dateRegex = /^\d{4}-\d{2}-\d{2}$/;
  if (!dateRegex.test(date) || isNaN(Date.parse(date))) {
    showSearchValidationError('Please enter a valid departure date (YYYY-MM-DD).', dateEl);
    return;
  }

  // 5. Validate return date (for round trips)
  if (tripType === 'roundtrip') {
    if (!returnDate) {
      showSearchValidationError('Please select a return date for your round trip.', returnDateEl);
      return;
    }
    if (!dateRegex.test(returnDate) || isNaN(Date.parse(returnDate))) {
      showSearchValidationError('Please enter a valid return date (YYYY-MM-DD).', returnDateEl);
      return;
    }
    if (returnDate < date) {
      showSearchValidationError('Return date cannot be earlier than your departure date.', returnDateEl);
      return;
    }
  }

  // 6. Validate passenger count
  if (isNaN(passengers) || passengers < 1 || passengers > 9) {
    showSearchValidationError('Please select a valid passenger count between 1 and 9.', passengersEl);
    return;
  }

  // Preserve the search criteria for What-If Simulator and tools
  lastSearchCriteria = {
    origin,
    destination,
    date,
    returnDate,
    tripType,
    passengers,
    travelClass
  };

  // Provide immediate loading feedback and prevent duplicate submissions
  isSearchingFlights = true;
  const searchBtn = document.getElementById('btn-search-flights') || document.querySelector('.btn-search');
  let originalBtnHtml = '';
  if (searchBtn) {
    originalBtnHtml = searchBtn.innerHTML;
    searchBtn.disabled = true;
    searchBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Searching Flights...';
  }

  // Immediately switch view so user sees loading state
  if (typeof switchView === 'function') {
    switchView('search-view');
  }

  const container = document.getElementById('flight-results-container');
  const countSpan = document.getElementById('results-count-text');
  const titleSpan = document.getElementById('search-header-title');

  if (titleSpan) {
    titleSpan.textContent = `${origin} → ${destination} Flight Options`;
  }
  if (countSpan) {
    countSpan.textContent = 'Searching scheduled flights...';
  }
  if (container) {
    container.innerHTML = `
      <div style="text-align: center; padding: 4rem 1rem; background: white; border-radius: var(--radius-lg); border: 1px solid var(--border);">
        <i class="fa-solid fa-plane-departure fa-spin" style="font-size: 2.6rem; color: var(--primary); margin-bottom: 1rem;"></i>
        <h3 style="font-weight: 700; color: #1e3a8a;">Discovering Optimal Flights...</h3>
        <p style="color: var(--text-muted); max-width: 520px; margin: 0.5rem auto 0 auto; line-height: 1.5;">
          Checking real scheduled flights for <strong>${origin}</strong> to <strong>${destination}</strong> on <strong>${date}</strong> (${passengers} traveler${passengers > 1 ? 's' : ''}, ${travelClass.toUpperCase()})
        </p>
      </div>
    `;
  }

  try {
    const data = await api.get('/flights/search', {
      origin,
      destination,
      date,
      return_date: tripType === 'roundtrip' ? returnDate : '',
      trip_type: tripType,
      passengers,
      class: travelClass,
      sort_by: sortBy
    });

    currentSearchResults = data.itineraries || [];
    renderSearchResults(currentSearchResults, {
      origin,
      destination,
      date,
      tripType,
      returnDate,
      passengers,
      returnItineraries: data.return_itineraries || []
    });
    updateFilterOptions(currentSearchResults);
  } catch (err) {
    console.error('Flight search error:', err);
    if (countSpan) {
      countSpan.textContent = 'Search failed';
    }
    if (container) {
      container.innerHTML = `
        <div style="background: white; border-radius: var(--radius-lg); padding: 3rem 1.5rem; text-align: center; border: 1px solid #fecaca;">
          <i class="fa-solid fa-triangle-exclamation" style="font-size: 2.6rem; color: var(--danger); margin-bottom: 1rem;"></i>
          <h3 style="font-weight: 800; color: #991b1b; margin-bottom: 0.5rem;">Unable to Load Flights</h3>
          <p style="color: var(--text-muted); max-width: 520px; margin: 0 auto 1.5rem auto; line-height: 1.5;">
            ${err.message || 'We encountered an issue communicating with the flight search service. Please check your connection or retry.'}
          </p>
          <div style="display: flex; justify-content: center; gap: 1rem; flex-wrap: wrap;">
            <button class="btn-search" onclick="performFlightSearch()">
              <i class="fa-solid fa-rotate-right"></i> Try Again
            </button>
            <button style="background: transparent; border: 1px solid var(--border); padding: 0.65rem 1.25rem; border-radius: 8px; font-weight: 700; cursor: pointer;" onclick="switchView('home-view')">
              <i class="fa-solid fa-arrow-left"></i> Modify Search Criteria
            </button>
          </div>
        </div>
      `;
    }
    showToast(err.message || 'Error fetching flights from backend', 'danger');
  } finally {
    isSearchingFlights = false;
    if (searchBtn) {
      searchBtn.disabled = false;
      searchBtn.innerHTML = originalBtnHtml || '<i class="fa-solid fa-magnifying-glass"></i> Search Flights';
    }
  }
}
window.performFlightSearch = performFlightSearch;

function openWhatIfSimulator() {
  const origin = (lastSearchCriteria && lastSearchCriteria.origin) || document.getElementById('search-origin')?.value || 'TIR';
  const destination = (lastSearchCriteria && lastSearchCriteria.destination) || document.getElementById('search-destination')?.value || 'DEL';
  const date = (lastSearchCriteria && lastSearchCriteria.date) || document.getElementById('search-date')?.value || '2026-10-23';
  const travelClass = (lastSearchCriteria && lastSearchCriteria.travelClass) || document.getElementById('search-class')?.value || 'economy';

  // Navigate to tools view
  if (typeof switchView === 'function') {
    switchView('tools-view');
  }

  // Activate What-If tab
  const whatifTabBtn = document.querySelector('#tools-view button[onclick*="whatif-tab"]');
  if (typeof switchToolTab === 'function') {
    switchToolTab('whatif-tab', whatifTabBtn);
  }

  // Populate simulator fields with user's search criteria
  const origInput = document.getElementById('whatif-origin');
  const destInput = document.getElementById('whatif-destination');
  const dateInput = document.getElementById('whatif-date');
  const classInput = document.getElementById('whatif-class');

  if (origInput) origInput.value = origin;
  if (destInput) destInput.value = destination;
  if (dateInput) dateInput.value = date;
  if (classInput) classInput.value = travelClass;

  // Run the simulation automatically
  if (typeof runWhatIfSimulator === 'function') {
    runWhatIfSimulator();
  }
}
window.openWhatIfSimulator = openWhatIfSimulator;

function renderSearchResults(itineraries, searchMeta = {}) {
  const container = document.getElementById('flight-results-container');
  const countSpan = document.getElementById('results-count-text');
  if (!container) return;

  const origin = searchMeta.origin || (lastSearchCriteria && lastSearchCriteria.origin) || 'Origin';
  const destination = searchMeta.destination || (lastSearchCriteria && lastSearchCriteria.destination) || 'Destination';
  const date = searchMeta.date || (lastSearchCriteria && lastSearchCriteria.date) || 'Selected Date';
  const passengers = searchMeta.passengers || (lastSearchCriteria && lastSearchCriteria.passengers) || 1;

  if (countSpan) {
    countSpan.textContent = `${itineraries.length} flight option${itineraries.length === 1 ? '' : 's'} found`;
  }

  if (itineraries.length === 0) {
    container.innerHTML = `
      <div style="background: white; border-radius: var(--radius-lg); padding: 3rem 1.5rem; text-align: center; border: 1px solid var(--border);">
        <i class="fa-solid fa-plane-slash" style="font-size: 2.8rem; color: var(--text-light); margin-bottom: 1rem;"></i>
        <h3 style="font-weight: 800; margin-bottom: 0.5rem; color: #1e293b;">No Scheduled Flights Found</h3>
        <p style="color: var(--text-muted); max-width: 540px; margin: 0 auto 1.5rem auto; line-height: 1.55; font-size: 0.95rem;">
          We could not find any active scheduled flights from <strong>${origin}</strong> to <strong>${destination}</strong> on <strong>${date}</strong> in the FlyWise database.
          <br><br>
          <span style="font-size: 0.85rem; color: #64748b;">
            💡 <em>Note: Our database currently contains scheduled domestic flights across major Indian airports (TIR, DEL, BOM, BLR, MAA, HYD, GOI, PNQ, JAI, DXB) for October - November 2026.</em>
          </span>
        </p>
        <div style="display: flex; justify-content: center; gap: 1rem; flex-wrap: wrap;">
          <button class="btn-search" style="padding: 0.65rem 1.5rem;" onclick="openWhatIfSimulator()">
            <i class="fa-solid fa-calendar-days"></i> Open What-If Date Simulator
          </button>
          <button style="background: transparent; border: 1px solid var(--border); padding: 0.65rem 1.25rem; border-radius: 8px; font-weight: 700; cursor: pointer;" onclick="switchView('home-view')">
            <i class="fa-solid fa-arrow-left"></i> Modify Search Criteria
          </button>
        </div>
      </div>
    `;
    return;
  }

  container.innerHTML = itineraries.map((it, idx) => {
    const isTop = idx === 0;
    const depTime = new Date(it.departure_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const arrTime = new Date(it.arrival_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const durHrs = Math.floor(it.duration_minutes / 60);
    const durMins = it.duration_minutes % 60;
    const flightNum = it.segments[0].flight_number;
    const isChecked = selectedForCompare.some(c => c.itinerary_id === it.itinerary_id);

    return `
      <div class="flight-card ${isTop ? 'top-recommended' : ''}" id="card-${it.itinerary_id}">
        <div class="flight-card-header">
          <div class="airline-badge-wrap">
            <div class="airline-logo-icon">
              ${it.airline_code}
            </div>
            <div class="airline-info">
              <h4>${it.airline_name}</h4>
              <div class="flight-number">${flightNum} • ${it.travel_class.toUpperCase()}</div>
            </div>
          </div>

          <div class="badges-row">
            ${isTop ? '<span style="background: #fef3c7; color: #b45309; padding: 2px 8px; border-radius: 9999px; font-size: 0.72rem; font-weight: 800;">★ TOP RECOMMENDED</span>' : ''}
            <div class="score-badge">
              <i class="fa-solid fa-chart-line"></i> Score: ${it.recommendation_score}/100
            </div>
            <span class="risk-badge ${it.connection_risk.risk_level}">
              ${it.connection_risk.risk_level} Risk
            </span>
          </div>
        </div>

        <div class="flight-card-body">
          <div class="route-timeline">
            <div class="time-point">
              <div class="time">${depTime}</div>
              <div class="airport-code">${it.origin_code}</div>
              <div class="city">${it.origin_city}</div>
            </div>

            <div class="duration-line">
              <div class="duration">${durHrs}h ${durMins}m</div>
              <div class="line"></div>
              <div class="stop-indicator">
                ${it.stops === 0 ? 'Direct Non-stop' : `1 Stop via ${it.connection_info ? it.connection_info.layover_airport : 'Transit'}`}
              </div>
            </div>

            <div class="time-point arr">
              <div class="time">${arrTime}</div>
              <div class="airport-code">${it.destination_code}</div>
              <div class="city">${it.destination_city}</div>
            </div>
          </div>

          <div class="price-cta-col">
            <div class="fare-amount">
              ₹${Number(it.total_fare).toLocaleString('en-IN')}
              ${passengers > 1 ? `<div style="font-size: 0.72rem; font-weight: 500; color: var(--text-muted);">₹${Number(it.total_fare * passengers).toLocaleString('en-IN')} for ${passengers} travelers</div>` : ''}
            </div>
            <div class="total-journey-est" onclick="openCostBreakdownModal('${it.itinerary_id}')" title="Click to view itemized breakdown">
              Est. Total: ₹${Number(it.estimated_journey_cost * passengers).toLocaleString('en-IN')} <i class="fa-solid fa-circle-info"></i>
            </div>
            <div style="display: flex; gap: 0.5rem; align-items: center; margin-top: 0.5rem;">
              <label style="font-size: 0.78rem; font-weight: 600; color: var(--text-muted); display: flex; align-items: center; gap: 4px; cursor: pointer;">
                <input type="checkbox" ${isChecked ? 'checked' : ''} onchange="toggleCompare('${it.itinerary_id}')"> Compare
              </label>
              <button class="btn-select-flight" onclick="startBookingFlow('${it.itinerary_id}')">
                Select Flight
              </button>
            </div>
          </div>
        </div>

        <div class="card-explanations">
          <div class="reasons-tags">
            ${it.explanations.map(r => `<span class="reason-tag"><i class="fa-solid fa-check" style="color: #10b981; font-size: 0.7rem;"></i> ${r}</span>`).join('')}
          </div>
          <span style="font-size: 0.75rem; color: #0284c7; cursor: pointer; font-weight: 600;" onclick="explainFlightScore('${it.itinerary_id}')">
            View Score Weights <i class="fa-solid fa-chevron-right" style="font-size: 0.65rem;"></i>
          </span>
        </div>
      </div>
    `;
  }).join('');
}

function updateFilterOptions(itineraries) {
  // Extract unique airlines
  const airlines = [...new Set(itineraries.map(it => it.airline_name))];
  const airlineContainer = document.getElementById('airline-filter-checkboxes');
  if (airlineContainer) {
    airlineContainer.innerHTML = airlines.map(al => `
      <label class="filter-checkbox-label">
        <input type="checkbox" value="${al}" onchange="applyFilters()">
        <span>${al}</span>
      </label>
    `).join('');
  }
}

function applyFilters() {
  let filtered = [...currentSearchResults];

  // Airline filter
  const checkedAirlines = Array.from(document.querySelectorAll('#airline-filter-checkboxes input:checked')).map(el => el.value);
  if (checkedAirlines.length > 0) {
    filtered = filtered.filter(it => checkedAirlines.includes(it.airline_name));
  }

  // Stops filter
  const stopFilters = Array.from(document.querySelectorAll('#stops-filter-checkboxes input:checked')).map(el => parseInt(el.value));
  if (stopFilters.length > 0) {
    filtered = filtered.filter(it => stopFilters.includes(it.stops));
  }

  // Max Price
  const maxPriceInput = document.getElementById('price-filter-range');
  if (maxPriceInput) {
    const maxVal = parseFloat(maxPriceInput.value);
    document.getElementById('price-range-val').textContent = `₹${maxVal.toLocaleString('en-IN')}`;
    filtered = filtered.filter(it => it.total_fare <= maxVal);
  }

  renderSearchResults(filtered);
}

function toggleCompare(itineraryId) {
  const item = currentSearchResults.find(it => it.itinerary_id === itineraryId);
  if (!item) return;

  const idx = selectedForCompare.findIndex(c => c.itinerary_id === itineraryId);
  if (idx > -1) {
    selectedForCompare.splice(idx, 1);
  } else {
    if (selectedForCompare.length >= 3) {
      showToast('You can compare a maximum of 3 flights simultaneously.', 'warning');
      const box = document.querySelector(`#card-${itineraryId} input[type="checkbox"]`);
      if (box) box.checked = false;
      return;
    }
    selectedForCompare.push(item);
  }

  updateCompareTray();
}

function updateCompareTray() {
  const tray = document.getElementById('compare-tray');
  const countSpan = document.getElementById('compare-count');
  const listSpan = document.getElementById('compare-items-list');

  if (!tray) return;

  if (selectedForCompare.length > 0) {
    tray.classList.add('show');
    if (countSpan) countSpan.textContent = selectedForCompare.length;
    if (listSpan) {
      listSpan.innerHTML = selectedForCompare.map(it => `
        <span style="background: rgba(255,255,255,0.15); padding: 4px 8px; border-radius: 4px; font-size: 0.82rem;">
          ${it.airline_name} (${it.segments[0].flight_number}) • ₹${it.total_fare.toLocaleString('en-IN')}
        </span>
      `).join('');
    }
  } else {
    tray.classList.remove('show');
  }
}

async function showComparisonModal() {
  if (selectedForCompare.length < 2) {
    showToast('Please select at least 2 flights to compare.', 'info');
    return;
  }

  const modal = document.getElementById('comparison-modal');
  const content = document.getElementById('comparison-modal-body');
  if (!modal || !content) return;

  const compData = await api.post('/recommendations/compare', { itineraries: selectedForCompare });
  const comp = compData.comparison;

  content.innerHTML = `
    <h3 style="font-weight: 800; margin-bottom: 0.5rem;">Intelligent Flight Comparison</h3>
    <div style="background: #ecfdf5; border: 1px solid #a7f3d0; padding: 0.85rem; border-radius: 8px; margin-bottom: 1.5rem; color: #065f46; font-size: 0.9rem;">
      <i class="fa-solid fa-award"></i> <strong>AI Winner:</strong> ${comp.reason}
    </div>

    <div style="display: grid; grid-template-columns: repeat(${selectedForCompare.length}, 1fr); gap: 1rem;">
      ${comp.items.map(it => `
        <div style="border: 2px solid ${it.itinerary_id === comp.best_overall ? '#10b981' : 'var(--border)'}; border-radius: 12px; padding: 1.25rem; background: ${it.itinerary_id === comp.best_overall ? '#f0fdf4' : 'white'}; position: relative;">
          ${it.itinerary_id === comp.best_overall ? '<span style="position: absolute; top: -10px; right: 12px; background: #10b981; color: white; font-size: 0.7rem; font-weight: 800; padding: 2px 8px; border-radius: 9999px;">TOP CHOICE</span>' : ''}
          <h4 style="font-weight: 800;">${it.airline_name}</h4>
          <div style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 1rem;">${it.segments[0].flight_number}</div>

          <div style="margin-bottom: 0.75rem;">
            <div style="font-size: 0.75rem; color: var(--text-muted); font-weight: 700;">TICKET PRICE</div>
            <div style="font-size: 1.4rem; font-weight: 800;">₹${it.total_fare.toLocaleString('en-IN')}</div>
          </div>

          <div style="margin-bottom: 0.75rem;">
            <div style="font-size: 0.75rem; color: var(--text-muted); font-weight: 700;">EST. TOTAL COST</div>
            <div style="font-size: 1.1rem; font-weight: 700; color: #0369a1;">₹${it.estimated_journey_cost.toLocaleString('en-IN')}</div>
          </div>

          <div style="margin-bottom: 0.75rem;">
            <div style="font-size: 0.75rem; color: var(--text-muted); font-weight: 700;">DURATION & STOPS</div>
            <div style="font-size: 0.9rem; font-weight: 600;">${Math.floor(it.duration_minutes / 60)}h ${it.duration_minutes % 60}m (${it.stops === 0 ? 'Direct' : '1 Stop'})</div>
          </div>

          <div style="margin-bottom: 0.75rem;">
            <div style="font-size: 0.75rem; color: var(--text-muted); font-weight: 700;">CONNECTION RISK</div>
            <span class="risk-badge ${it.connection_risk.risk_level}">${it.connection_risk.risk_level} Risk</span>
          </div>

          <div style="margin-bottom: 1.25rem;">
            <div style="font-size: 0.75rem; color: var(--text-muted); font-weight: 700;">RECOMMENDATION SCORE</div>
            <div style="font-size: 1.1rem; font-weight: 800; color: #059669;">${it.recommendation_score} / 100</div>
          </div>

          <button class="btn-select-flight" style="width: 100%;" onclick="closeModal('comparison-modal'); startBookingFlow('${it.itinerary_id}')">
            Select This Flight
          </button>
        </div>
      `).join('')}
    </div>
  `;

  openModal('comparison-modal');
}
