/**
 * FlyWise AI - Flight Search & Comparison Module
 */

let currentSearchResults = [];
let selectedForCompare = [];

async function performFlightSearch(e) {
  if (e) e.preventDefault();

  const origin = document.getElementById('search-origin').value.trim();
  const destination = document.getElementById('search-destination').value.trim();
  const date = document.getElementById('search-date').value;
  const travelClass = document.getElementById('search-class').value;
  const sortBy = document.getElementById('sort-by-select') ? document.getElementById('sort-by-select').value : 'recommendation';

  if (!origin || !destination || !date) {
    showToast('Please specify Origin, Destination and Departure Date.', 'warning');
    return;
  }

  const container = document.getElementById('flight-results-container');
  if (container) {
    container.innerHTML = `
      <div style="text-align: center; padding: 4rem 1rem;">
        <i class="fa-solid fa-plane-departure fa-spin" style="font-size: 2.5rem; color: var(--primary); margin-bottom: 1rem;"></i>
        <h3 style="font-weight: 700;">Discovering Optimal Flights...</h3>
        <p style="color: var(--text-muted);">Ranking schedules, assessing connection safety, and calculating journey costs</p>
      </div>
    `;
  }

  try {
    const data = await api.get('/flights/search', {
      origin,
      destination,
      date,
      class: travelClass,
      sort_by: sortBy
    });

    currentSearchResults = data.itineraries || [];
    renderSearchResults(currentSearchResults);
    updateFilterOptions(currentSearchResults);

    // Switch to search view if not active
    switchView('search-view');
  } catch (err) {
    if (container) {
      container.innerHTML = `
        <div style="text-align: center; padding: 3rem 1rem;">
          <i class="fa-solid fa-triangle-exclamation" style="font-size: 2rem; color: var(--danger); margin-bottom: 0.5rem;"></i>
          <p style="font-weight: 700;">${err.message || 'Error fetching flights'}</p>
        </div>
      `;
    }
  }
}

function renderSearchResults(itineraries) {
  const container = document.getElementById('flight-results-container');
  const countSpan = document.getElementById('results-count-text');
  if (!container) return;

  if (countSpan) {
    countSpan.textContent = `${itineraries.length} flights found`;
  }

  if (itineraries.length === 0) {
    container.innerHTML = `
      <div style="background: white; border-radius: var(--radius-lg); padding: 3rem; text-align: center; border: 1px solid var(--border);">
        <i class="fa-solid fa-plane-slash" style="font-size: 2.5rem; color: var(--text-light); margin-bottom: 1rem;"></i>
        <h3 style="font-weight: 700; margin-bottom: 0.5rem;">No flights found for this route & date</h3>
        <p style="color: var(--text-muted); margin-bottom: 1.5rem;">Try shifting dates using our What-If Simulator or searching nearby alternative airports.</p>
        <button class="btn-search" style="margin: 0 auto;" onclick="openWhatIfSimulator()">Open What-If Date Simulator</button>
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
            <div class="fare-amount">₹${Number(it.total_fare).toLocaleString('en-IN')}</div>
            <div class="total-journey-est" onclick="openCostBreakdownModal('${it.itinerary_id}')" title="Click to view itemized breakdown">
              Est. Total: ₹${Number(it.estimated_journey_cost).toLocaleString('en-IN')} <i class="fa-solid fa-circle-info"></i>
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
