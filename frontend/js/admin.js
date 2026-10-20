/**
 * FlyWise AI - Administrative Management & AI Monitoring Module
 */

let airlineChart = null;
let statusChart = null;
let latencyChart = null;

async function loadAdminDashboard() {
  const container = document.getElementById('admin-content-pane');
  if (!container) return;

  const user = api.getUser();
  if (!user || user.role !== 'admin') {
    container.innerHTML = `
      <div style="text-align: center; padding: 4rem 1rem;">
        <i class="fa-solid fa-lock" style="font-size: 2.5rem; color: var(--danger); margin-bottom: 1rem;"></i>
        <h3 style="font-weight: 800;">Administrator Access Required</h3>
        <p style="color: var(--text-muted); margin-bottom: 1.5rem;">Please log in with an administrator account to view system operations, triggers, and analytics.</p>
        <button class="btn-search" style="margin: 0 auto;" onclick="openAuthModal('login')">Admin Log In</button>
      </div>
    `;
    return;
  }

  container.innerHTML = `
    <div style="text-align: center; padding: 3rem;"><i class="fa-solid fa-spinner fa-spin" style="font-size: 2rem; color: var(--primary);"></i><p style="margin-top: 0.5rem;">Loading DBMS operational analytics...</p></div>
  `;

  try {
    const stats = await api.get('/admin/dashboard');
    const analytics = await api.get('/admin/analytics');
    const aiUsage = await api.get('/admin/ai-usage');

    renderAdminDashboardView(container, stats, analytics, aiUsage);
  } catch (err) {
    container.innerHTML = `<div style="color: var(--danger); font-weight: 700;">${err.message}</div>`;
  }
}

function renderAdminDashboardView(container, stats, analytics, aiUsage) {
  const c = stats.counts;

  container.innerHTML = `
    <!-- KPI Header Row -->
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 1rem; margin-bottom: 2rem;">
      <div style="background: white; border: 1px solid var(--border); border-radius: var(--radius-md); padding: 1.25rem; box-shadow: var(--shadow-sm);">
        <span style="font-size: 0.75rem; font-weight: 700; color: var(--text-muted);">TOTAL FLIGHTS</span>
        <div style="font-size: 1.8rem; font-weight: 800; color: var(--primary);">${c.total_flights}</div>
      </div>
      <div style="background: white; border: 1px solid var(--border); border-radius: var(--radius-md); padding: 1.25rem; box-shadow: var(--shadow-sm);">
        <span style="font-size: 0.75rem; font-weight: 700; color: var(--text-muted);">BOOKINGS CONFIRMED</span>
        <div style="font-size: 1.8rem; font-weight: 800; color: #059669;">${c.total_bookings}</div>
      </div>
      <div style="background: white; border: 1px solid var(--border); border-radius: var(--radius-md); padding: 1.25rem; box-shadow: var(--shadow-sm);">
        <span style="font-size: 0.75rem; font-weight: 700; color: var(--text-muted);">TOTAL REVENUE</span>
        <div style="font-size: 1.8rem; font-weight: 800; color: var(--text-main);">₹${Number(c.total_revenue).toLocaleString('en-IN')}</div>
      </div>
      <div style="background: white; border: 1px solid var(--border); border-radius: var(--radius-md); padding: 1.25rem; box-shadow: var(--shadow-sm);">
        <span style="font-size: 0.75rem; font-weight: 700; color: var(--text-muted);">REGISTERED USERS</span>
        <div style="font-size: 1.8rem; font-weight: 800; color: #0284c7;">${c.total_users}</div>
      </div>
      <div style="background: white; border: 1px solid var(--border); border-radius: var(--radius-md); padding: 1.25rem; box-shadow: var(--shadow-sm);">
        <span style="font-size: 0.75rem; font-weight: 700; color: var(--text-muted);">ACTIVE AIRCRAFT</span>
        <div style="font-size: 1.8rem; font-weight: 800; color: #d97706;">${c.active_aircraft}</div>
      </div>
      <div style="background: white; border: 1px solid var(--border); border-radius: var(--radius-md); padding: 1.25rem; box-shadow: var(--shadow-sm);">
        <span style="font-size: 0.75rem; font-weight: 700; color: var(--text-muted);">AI REQUEST LOGS</span>
        <div style="font-size: 1.8rem; font-weight: 800; color: #7c3aed;">${c.total_ai_requests}</div>
      </div>
    </div>

    <!-- Chart.js Visualizations Grid -->
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-bottom: 2rem;">
      <div style="background: white; border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 1.5rem;">
        <h4 style="font-weight: 800; margin-bottom: 1rem;"><i class="fa-solid fa-chart-pie"></i> Airline Market Share (Bookings)</h4>
        <div style="height: 250px; position: relative;">
          <canvas id="chart-airline-bookings"></canvas>
        </div>
      </div>
      <div style="background: white; border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 1.5rem;">
        <h4 style="font-weight: 800; margin-bottom: 1rem;"><i class="fa-solid fa-chart-column"></i> Schedule Status Distribution</h4>
        <div style="height: 250px; position: relative;">
          <canvas id="chart-flight-status"></canvas>
        </div>
      </div>
    </div>

    <!-- Operations & Trigger Test Section -->
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-bottom: 2rem;">
      <!-- Flight Status Updater (Triggering trg_after_flight_status_update) -->
      <div style="background: white; border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 1.5rem;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
          <h4 style="font-weight: 800;"><i class="fa-solid fa-bolt" style="color: #f59e0b;"></i> Trigger Demonstration</h4>
          <span style="font-size: 0.75rem; background: #fef3c7; color: #b45309; padding: 2px 6px; border-radius: 4px; font-weight: 700;">DBMS Trigger</span>
        </div>
        <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 1rem;">
          Updating a flight status fires <code>trg_after_flight_status_update</code>, logging changes to <code>flight_status_history</code> table.
        </p>

        <div style="display: flex; gap: 0.75rem; margin-bottom: 0.75rem;">
          <input type="number" id="admin-flight-id" placeholder="Flight ID (e.g. 5)" style="padding: 0.5rem; border: 1px solid var(--border); border-radius: 6px; width: 120px;" value="5">
          <select id="admin-status-select" style="padding: 0.5rem; border: 1px solid var(--border); border-radius: 6px; flex: 1;">
            <option value="on-time">Mark ON-TIME</option>
            <option value="delayed">Mark DELAYED (+45m)</option>
            <option value="boarding">Mark BOARDING</option>
            <option value="departed">Mark DEPARTED</option>
            <option value="cancelled">Mark CANCELLED</option>
          </select>
          <button class="btn-search" style="height: 38px; padding: 0 1rem; font-size: 0.85rem;" onclick="triggerFlightUpdate()">Update Status</button>
        </div>
      </div>

      <!-- AI Usage Monitoring Summary -->
      <div style="background: white; border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 1.5rem;">
        <h4 style="font-weight: 800; margin-bottom: 0.5rem;"><i class="fa-solid fa-microchip" style="color: #7c3aed;"></i> Gemini Model Telemetry</h4>
        <div style="display: flex; gap: 1.5rem; margin-top: 0.75rem;">
          <div>
            <div style="font-size: 0.75rem; color: var(--text-muted);">AVERAGE LATENCY</div>
            <div style="font-size: 1.4rem; font-weight: 800;">${aiUsage.summary ? aiUsage.summary.avg_latency_ms : 450} ms</div>
          </div>
          <div>
            <div style="font-size: 0.75rem; color: var(--text-muted);">SUCCESS RATE</div>
            <div style="font-size: 1.4rem; font-weight: 800; color: #059669;">
              ${aiUsage.summary && aiUsage.summary.total_calls > 0 ? Math.round((aiUsage.summary.successful_calls / aiUsage.summary.total_calls) * 100) : 100}%
            </div>
          </div>
          <div>
            <div style="font-size: 0.75rem; color: var(--text-muted);">DEPLOYED MODEL</div>
            <div style="font-size: 1.1rem; font-weight: 800; color: var(--primary);">gemini-3.5-flash</div>
          </div>
        </div>
      </div>
    </div>
  `;

  // Render Chart.js
  renderCharts(analytics.charts);
}

function renderCharts(chartsData) {
  if (typeof Chart === 'undefined') return;

  // 1. Airline Bookings Doughnut
  const ctx1 = document.getElementById('chart-airline-bookings');
  if (ctx1) {
    if (airlineChart) airlineChart.destroy();
    airlineChart = new Chart(ctx1, {
      type: 'doughnut',
      data: {
        labels: chartsData.airline_bookings.labels,
        datasets: [{
          data: chartsData.airline_bookings.data,
          backgroundColor: ['#1e40af', '#0284c7', '#059669', '#f59e0b', '#dc2626']
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: 'bottom' } }
      }
    });
  }

  // 2. Status Distribution Bar
  const ctx2 = document.getElementById('chart-flight-status');
  if (ctx2) {
    if (statusChart) statusChart.destroy();
    statusChart = new Chart(ctx2, {
      type: 'bar',
      data: {
        labels: chartsData.status_distribution.labels,
        datasets: [{
          label: 'Scheduled Flights',
          data: chartsData.status_distribution.data,
          backgroundColor: '#3b82f6'
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true } }
      }
    });
  }
}

async function triggerFlightUpdate() {
  const flightId = document.getElementById('admin-flight-id').value;
  const status = document.getElementById('admin-status-select').value;
  if (!flightId) return;

  try {
    await api.patch(`/admin/flights/${flightId}`, { flight_status: status });
    showToast(`Flight ${flightId} updated to ${status.toUpperCase()}! Trigger recorded history.`, 'success');
  } catch (err) {
    showToast(err.message, 'danger');
  }
}
