/**
 * FlyWise AI - Smart Travel Planning Tools Module
 */

// 1. What-If Simulator
async function runWhatIfSimulator() {
  const originInput = document.getElementById('whatif-origin');
  const destinationInput = document.getElementById('whatif-destination');
  const dateInput = document.getElementById('whatif-date');
  const classInput = document.getElementById('whatif-class');

  const origin = originInput ? originInput.value.trim().toUpperCase() : 'TIR';
  const destination = destinationInput ? destinationInput.value.trim().toUpperCase() : 'DEL';
  const date = dateInput ? dateInput.value.trim() : '2026-10-23';
  const travelClass = classInput ? classInput.value : 'economy';

  const container = document.getElementById('whatif-results');
  if (!container) return;

  if (!origin || !destination || !date) {
    showToast('Please specify Origin, Destination and Baseline Date.', 'warning');
    return;
  }

  container.innerHTML = `
    <div style="text-align: center; padding: 2.5rem 1rem;">
      <i class="fa-solid fa-spinner fa-spin" style="font-size: 1.8rem; color: var(--primary); margin-bottom: 0.75rem;"></i>
      <h4 style="font-weight: 700;">Simulating Fare Variations for ${origin} → ${destination}...</h4>
      <p style="color: var(--text-muted); font-size: 0.85rem;">Checking scheduled flights and benchmark fare trends across ±3 days</p>
    </div>
  `;

  try {
    const data = await api.post('/simulation/alternatives', {
      origin,
      destination,
      departure_date: date,
      travel_class: travelClass
    });

    if (!data || !data.timeline || data.timeline.length === 0) {
      container.innerHTML = `
        <div style="background: #f8fafc; border: 1px dashed var(--border); border-radius: 8px; padding: 2rem; text-align: center;">
          <i class="fa-solid fa-calendar-xmark" style="font-size: 2rem; color: var(--text-light); margin-bottom: 0.5rem;"></i>
          <p style="color: var(--text-muted); font-weight: 600;">No simulation data available for this route.</p>
        </div>
      `;
      return;
    }

    const baselineFare = Number(data.baseline_fare || 0);

    container.innerHTML = `
      <!-- Summary Bar -->
      <div style="background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 10px; padding: 1.15rem; margin-bottom: 1.5rem;">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.75rem; border-bottom: 1px solid #dbeafe; padding-bottom: 0.75rem; margin-bottom: 0.75rem;">
          <div>
            <h4 style="font-weight: 800; color: #1e3a8a; margin: 0;">
              <i class="fa-solid fa-calendar-days" style="color: var(--primary);"></i> Alternative Dates for ${data.origin} → ${data.destination}
            </h4>
            <span style="font-size: 0.78rem; color: #3b82f6;">Baseline: <strong>${data.base_date}</strong> • Class: <strong>${(data.travel_class || 'economy').toUpperCase()}</strong></span>
          </div>
          ${data.max_savings_inr > 0 ? `
            <span style="background: #10b981; color: white; padding: 4px 10px; border-radius: 9999px; font-size: 0.8rem; font-weight: 800;">
              <i class="fa-solid fa-piggy-bank"></i> Potential Savings: Up to ₹${Number(data.max_savings_inr).toLocaleString('en-IN')}
            </span>
          ` : `
            <span style="background: #e2e8f0; color: #475569; padding: 4px 10px; border-radius: 9999px; font-size: 0.78rem; font-weight: 700;">
              Best Available Rate on Selected Date
            </span>
          `}
        </div>

        <p style="font-size: 0.86rem; color: #1e40af; line-height: 1.45; margin: 0;">
          <i class="fa-solid fa-circle-info"></i> ${data.insights.join(' ')}
        </p>
      </div>

      <!-- 7-Day Alternative Dates Grid -->
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(135px, 1fr)); gap: 0.85rem; margin-bottom: 1rem;">
        ${data.timeline.map(t => {
          const isBase = t.shift_days === 0;
          const isCheapest = t.date === data.best_date;
          const isScheduled = Boolean(t.is_live_schedule || t.flight_count > 0);
          const fareDiff = Number(t.fare_difference || 0);

          let diffBadge = '';
          if (isBase) {
            diffBadge = `<span style="font-size: 0.72rem; color: var(--primary); font-weight: 700;">Baseline Date</span>`;
          } else if (fareDiff < 0) {
            diffBadge = `<span style="font-size: 0.72rem; color: #059669; font-weight: 800;"><i class="fa-solid fa-arrow-down"></i> Save ₹${Math.abs(fareDiff).toLocaleString('en-IN')}</span>`;
          } else if (fareDiff > 0) {
            diffBadge = `<span style="font-size: 0.72rem; color: #b45309; font-weight: 700;"><i class="fa-solid fa-arrow-up"></i> +₹${fareDiff.toLocaleString('en-IN')}</span>`;
          } else {
            diffBadge = `<span style="font-size: 0.72rem; color: var(--text-muted); font-weight: 600;">Same Fare</span>`;
          }

          return `
            <div style="border: 2px solid ${isCheapest ? '#10b981' : isBase ? 'var(--primary)' : 'var(--border)'}; border-radius: 10px; padding: 0.85rem 0.65rem; text-align: center; background: ${isCheapest ? '#ecfdf5' : isBase ? '#f0f7ff' : '#ffffff'}; display: flex; flex-direction: column; justify-content: space-between; transition: transform 0.15s ease;">
              <div>
                <div style="font-size: 0.78rem; font-weight: 800; color: #0f172a;">${t.day_name}</div>
                <div style="font-size: 0.7rem; color: var(--text-muted); margin-bottom: 0.4rem;">
                  ${t.shift_days === 0 ? 'Selected' : `${t.shift_days > 0 ? '+' : ''}${t.shift_days} days`}
                </div>

                <div style="font-size: 1.25rem; font-weight: 800; margin: 0.25rem 0; color: ${isCheapest ? '#059669' : '#0f172a'};">
                  ₹${Number(t.lowest_fare).toLocaleString('en-IN')}
                </div>

                <div style="margin-bottom: 0.35rem;">
                  ${isScheduled ? `
                    <span style="display: inline-block; font-size: 0.66rem; font-weight: 700; background: #e0f2fe; color: #0284c7; padding: 1px 6px; border-radius: 4px;" title="Scheduled flights found in database">
                      <i class="fa-solid fa-check"></i> Live Schedule (${t.flight_count})
                    </span>
                  ` : `
                    <span style="display: inline-block; font-size: 0.66rem; font-weight: 600; background: #fef3c7; color: #92400e; padding: 1px 6px; border-radius: 4px;" title="Estimated historical price trend (no direct schedules recorded)">
                      <i class="fa-solid fa-calculator"></i> Estimated Trend
                    </span>
                  `}
                </div>

                <div style="min-height: 18px; margin-bottom: 0.5rem;">
                  ${diffBadge}
                </div>
              </div>

              <div>
                ${isScheduled ? `
                  <button class="btn-search" style="width: 100%; padding: 0.4rem 0.5rem; font-size: 0.72rem; font-weight: 700; border-radius: 6px;" onclick="applySimulatorDateAndSearch('${t.date}')">
                    <i class="fa-solid fa-magnifying-glass"></i> View Flights
                  </button>
                ` : `
                  <button style="width: 100%; padding: 0.4rem 0.5rem; font-size: 0.72rem; font-weight: 600; border-radius: 6px; border: 1px solid var(--border); background: #ffffff; cursor: pointer;" onclick="setSimulatorDate('${t.date}')">
                    <i class="fa-solid fa-calendar-day"></i> Shift Baseline
                  </button>
                `}
              </div>
            </div>
          `;
        }).join('')}
      </div>

      <div style="font-size: 0.74rem; color: var(--text-muted); text-align: center; margin-top: 0.5rem;">
        <i class="fa-solid fa-circle-check" style="color: #059669;"></i> <strong>Live Schedule:</strong> Actual fares queried from MySQL. 
        <i class="fa-solid fa-chart-line" style="color: #d97706; margin-left: 0.75rem;"></i> <strong>Estimated Trend:</strong> Benchmark cost indicators for dates outside current schedule.
      </div>
    `;
  } catch (err) {
    container.innerHTML = `
      <div style="background: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; padding: 1.5rem; text-align: center;">
        <i class="fa-solid fa-triangle-exclamation" style="color: var(--danger); font-size: 1.5rem; margin-bottom: 0.5rem;"></i>
        <h4 style="color: #991b1b; font-weight: 800;">Simulation Error</h4>
        <p style="color: #7f1d1d; font-size: 0.85rem; margin-bottom: 1rem;">${err.message || 'Unable to connect to the simulation engine.'}</p>
        <button class="btn-search" style="padding: 0.5rem 1rem; font-size: 0.8rem;" onclick="runWhatIfSimulator()">
          <i class="fa-solid fa-rotate-right"></i> Retry Simulation
        </button>
      </div>
    `;
  }
}

/**
 * Applies a shifted date from What-If Simulator directly into Flight Search and runs search.
 */
function applySimulatorDateAndSearch(dateStr) {
  const origin = document.getElementById('whatif-origin')?.value.trim().toUpperCase() || 'TIR';
  const destination = document.getElementById('whatif-destination')?.value.trim().toUpperCase() || 'DEL';
  const travelClass = document.getElementById('whatif-class')?.value || 'economy';

  const origInput = document.getElementById('search-origin');
  const destInput = document.getElementById('search-destination');
  const dateInput = document.getElementById('search-date');
  const classInput = document.getElementById('search-class');

  if (origInput) origInput.value = origin;
  if (destInput) destInput.value = destination;
  if (dateInput) dateInput.value = dateStr;
  if (classInput) classInput.value = travelClass;

  switchView('home-view');
  performFlightSearch();
  showToast(`Applied shifted date ${dateStr} for ${origin} → ${destination}.`, 'info');
}

/**
 * Shifts baseline date in What-If Simulator and re-runs simulation.
 */
function setSimulatorDate(dateStr) {
  const dateInput = document.getElementById('whatif-date');
  if (dateInput) {
    dateInput.value = dateStr;
    runWhatIfSimulator();
    showToast(`Shifted baseline date to ${dateStr}.`, 'info');
  }
}

// 2. Alternative Airport Finder
async function runAlternativeAirports() {
  const origin = document.getElementById('altairport-origin').value.trim().toUpperCase() || 'TIR';
  const destination = document.getElementById('altairport-dest').value.trim().toUpperCase() || 'DEL';
  const date = document.getElementById('altairport-date').value || '2026-10-23';

  const container = document.getElementById('altairport-results');
  if (!container) return;

  container.innerHTML = `<div style="text-align: center; padding: 2rem;"><i class="fa-solid fa-spinner fa-spin" style="font-size: 1.5rem; color: var(--primary);"></i><p style="margin-top: 0.5rem;">Analyzing nearby airport options & ground transit...</p></div>`;

  try {
    const data = await api.post('/simulation/airports', {
      origin,
      destination,
      departure_date: date
    });

    if (data.alternatives.length === 0) {
      container.innerHTML = `<p style="color: var(--text-muted); text-align: center; padding: 1rem;">No practical nearby airport alternatives mapped for ${origin}. Flying directly remains the most convenient route.</p>`;
      return;
    }

    container.innerHTML = data.alternatives.map(alt => `
      <div style="border: 1px solid var(--border); border-radius: 10px; padding: 1.25rem; margin-bottom: 1rem; background: white;">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.75rem;">
          <div>
            <h4 style="font-weight: 800; color: var(--primary);">Alternative Hub: ${alt.alternative_airport_code} (${alt.distance_km} km away)</h4>
            <div style="font-size: 0.85rem; color: var(--text-muted);">
              Ground Travel Time: <strong>~${alt.road_travel_hours} hours</strong> by road/cab (Est. Cab: ₹${alt.ground_cab_cost_inr.toLocaleString('en-IN')})
            </div>
          </div>
          <div style="text-align: right;">
            <div style="font-size: 0.75rem; color: var(--text-muted);">COMBINED TOTAL COST</div>
            <div style="font-size: 1.35rem; font-weight: 800;">₹${alt.total_journey_cost_inr.toLocaleString('en-IN')}</div>
          </div>
        </div>

        <div style="background: #f8fafc; border-left: 3px solid #0284c7; padding: 0.65rem 0.85rem; border-radius: 4px; font-size: 0.82rem; color: #0369a1;">
          <strong>Recommendation:</strong> ${alt.recommendation}
        </div>
      </div>
    `).join('');
  } catch (err) {
    container.innerHTML = `<div style="color: var(--danger);">${err.message}</div>`;
  }
}

// 3. Smart Baggage Calculator
async function calculateBaggageRules() {
  const airline = document.getElementById('baggage-airline-select').value;
  const tClass = document.getElementById('baggage-class-select').value;
  const weight = parseFloat(document.getElementById('baggage-weight-input').value) || 15;

  const container = document.getElementById('baggage-calc-results');
  if (!container) return;

  try {
    const data = await api.post('/baggage/interpret', {
      airline_code: airline,
      travel_class: tClass,
      expected_weight_kg: weight
    });

    container.innerHTML = `
      <div style="background: white; border: 1px solid var(--border); border-radius: 10px; padding: 1.25rem;">
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); padding-bottom: 0.75rem; margin-bottom: 1rem;">
          <h4 style="font-weight: 800;">${data.airline} (${data.airline_code}) Policy</h4>
          <span style="font-size: 0.8rem; background: var(--primary-light); color: var(--primary); padding: 2px 8px; border-radius: 4px; font-weight: 700;">${data.travel_class.toUpperCase()}</span>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1rem;">
          <div>
            <div style="font-size: 0.75rem; color: var(--text-muted); font-weight: 700;">FREE CHECKED ALLOWANCE</div>
            <div style="font-size: 1.25rem; font-weight: 800;">${data.free_checkin_allowance_kg} kg</div>
          </div>
          <div>
            <div style="font-size: 0.75rem; color: var(--text-muted); font-weight: 700;">CABIN BAGGAGE</div>
            <div style="font-size: 1.25rem; font-weight: 800;">${data.cabin_allowance}</div>
          </div>
        </div>

        ${data.excess_weight_kg > 0 ? `
          <div style="background: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; padding: 0.85rem; margin-bottom: 1rem;">
            <strong style="color: #991b1b;">Excess Baggage: ${data.excess_weight_kg} kg</strong>
            <div style="font-size: 0.85rem; color: #7f1d1d; margin-top: 2px;">
              Estimated Excess Charge: <strong>₹${data.excess_charge_inr.toLocaleString('en-IN')}</strong> (Rate: ₹${data.excess_rate_per_kg}/kg)
            </div>
          </div>
        ` : `
          <div style="background: #ecfdf5; border: 1px solid #a7f3d0; border-radius: 8px; padding: 0.75rem; margin-bottom: 1rem; color: #065f46; font-size: 0.85rem;">
            <i class="fa-solid fa-circle-check"></i> Your baggage weight (${data.expected_weight_kg} kg) is within the free allowance.
          </div>
        `}

        <h5 style="font-weight: 700; font-size: 0.82rem; margin-bottom: 0.4rem; color: var(--text-muted);">CRITICAL DGCA RESTRICTIONS</h5>
        <ul style="font-size: 0.78rem; color: var(--text-muted); padding-left: 1.2rem;">
          ${data.critical_restrictions.map(r => `<li>${r}</li>`).join('')}
        </ul>
      </div>
    `;
  } catch (err) {
    container.innerHTML = `<div style="color: var(--danger);">${err.message}</div>`;
  }
}

// 4. Booking Verification & Scam Assistant
async function runScamAnalysis() {
  const text = document.getElementById('scam-message-text').value.trim();
  const container = document.getElementById('scam-results');
  if (!container || !text) {
    showToast('Please paste a message or notification text to analyze.', 'warning');
    return;
  }

  container.innerHTML = `<div style="text-align: center; padding: 2rem;"><i class="fa-solid fa-spinner fa-spin" style="font-size: 1.5rem; color: var(--primary);"></i><p style="margin-top: 0.5rem;">Analyzing phishing, threat patterns, and credential risks...</p></div>`;

  try {
    const data = await api.post('/verification/analyze-message', { message_text: text });

    const isHigh = data.verdict.includes('HIGH');
    container.innerHTML = `
      <div style="background: ${isHigh ? '#fef2f2' : '#f0fdf4'}; border: 1px solid ${isHigh ? '#fecaca' : '#bbf7d0'}; border-radius: 10px; padding: 1.25rem;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
          <h4 style="font-weight: 800; color: ${isHigh ? '#991b1b' : '#166534'};">${data.verdict}</h4>
          <span style="font-weight: 800; font-size: 0.85rem; color: ${isHigh ? '#b91c1c' : '#15803d'};">Risk Score: ${data.risk_score}/100</span>
        </div>

        <p style="font-size: 0.9rem; font-weight: 600; color: ${isHigh ? '#7f1d1d' : '#14532d'}; margin-bottom: 1rem;">
          ${data.advice}
        </p>

        ${data.red_flags.length > 0 ? `
          <h5 style="font-weight: 700; font-size: 0.85rem; color: #991b1b; margin-bottom: 0.4rem;">Identified Red Flags:</h5>
          <ul style="font-size: 0.82rem; color: #7f1d1d; padding-left: 1.25rem; margin-bottom: 1rem;">
            ${data.red_flags.map(f => `<li>${f}</li>`).join('')}
          </ul>
        ` : ''}

        <div style="background: white; border: 1px solid var(--border); border-radius: 8px; padding: 0.75rem; font-size: 0.8rem; color: var(--text-muted);">
          <strong>Verification Checklist:</strong>
          <ul style="padding-left: 1.2rem; margin-top: 0.35rem;">
            ${data.verification_checklist.map(c => `<li>${c}</li>`).join('')}
          </ul>
        </div>
      </div>
    `;
  } catch (err) {
    container.innerHTML = `<div style="color: var(--danger);">${err.message}</div>`;
  }
}

// 5. Group Travel Optimizer
async function runGroupOptimization() {
  const container = document.getElementById('group-optimizer-results');
  if (!container) return;

  container.innerHTML = `<div style="text-align: center; padding: 2rem;"><i class="fa-solid fa-spinner fa-spin" style="font-size: 1.5rem; color: var(--primary);"></i><p style="margin-top: 0.5rem;">Consolidating group budgets & schedule preferences...</p></div>`;

  try {
    const data = await api.post('/groups/1/optimise');

    container.innerHTML = `
      <div style="background: white; border: 1px solid var(--border); border-radius: 10px; padding: 1.25rem;">
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); padding-bottom: 0.75rem; margin-bottom: 1rem;">
          <div>
            <h4 style="font-weight: 800;">${data.group_name}</h4>
            <div style="font-size: 0.8rem; color: var(--text-muted);">${data.member_count} Members • Lowest Individual Budget: ₹${data.min_member_budget_inr.toLocaleString('en-IN')}</div>
          </div>
          <span style="background: var(--primary-light); color: var(--primary); font-size: 0.8rem; font-weight: 700; padding: 3px 8px; border-radius: 4px;">Group Sync Active</span>
        </div>

        <div style="display: flex; flex-direction: column; gap: 0.75rem;">
          ${data.suitable_flights.map(f => `
            <div style="border: 1px solid var(--border); border-radius: 8px; padding: 0.85rem; display: flex; justify-content: space-between; align-items: center; background: ${f.affordable_for_all ? '#ecfdf5' : '#f8fafc'};">
              <div>
                <strong style="color: var(--primary);">${f.airline} (${f.flight_number})</strong>
                <div style="font-size: 0.8rem; color: var(--text-muted);">${f.departure_time.split('T')[1].slice(0,5)} • ${f.duration} (${f.stops === 0 ? 'Direct' : '1 Stop'})</div>
                <div style="font-size: 0.75rem; font-weight: 600; color: ${f.affordable_for_all ? '#059669' : '#b45309'}; margin-top: 2px;">
                  ${f.budget_status}
                </div>
              </div>
              <div style="text-align: right;">
                <div style="font-size: 1.15rem; font-weight: 800;">₹${f.individual_fare_inr.toLocaleString('en-IN')}<span style="font-size: 0.75rem; font-weight: 400; color: var(--text-muted);">/person</span></div>
                <div style="font-size: 0.75rem; color: var(--text-muted);">Total: ₹${f.group_total_inr.toLocaleString('en-IN')}</div>
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  } catch (err) {
    container.innerHTML = `<div style="color: var(--danger);">${err.message}</div>`;
  }
}
