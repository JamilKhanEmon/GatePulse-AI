// Parking Movement Log

const DetectionTable = (() => {

  const VEHICLE_SVGS = {
    Bike: `<svg viewBox="0 0 52 36" fill="none" xmlns="http://www.w3.org/2000/svg" width="52" height="36"><rect width="52" height="36" rx="4" fill="#1e293b"/><circle cx="14" cy="24" r="7" stroke="#818cf8" stroke-width="1.8"/><circle cx="38" cy="24" r="7" stroke="#818cf8" stroke-width="1.8"/><path d="M14 24L24 16L32 20L38 24" stroke="#818cf8" stroke-width="1.8"/><path d="M24 16L22 10H18" stroke="#818cf8" stroke-width="1.8"/></svg>`,
    CNG: `<svg viewBox="0 0 52 36" fill="none" xmlns="http://www.w3.org/2000/svg" width="52" height="36"><rect width="52" height="36" rx="4" fill="#1e293b"/><rect x="8" y="10" width="34" height="16" rx="3" fill="none" stroke="#34d399" stroke-width="1.8"/><circle cx="16" cy="27" r="4" stroke="#34d399" stroke-width="1.8"/><circle cx="34" cy="27" r="4" stroke="#34d399" stroke-width="1.8"/></svg>`,
    Auto: `<svg viewBox="0 0 52 36" fill="none" xmlns="http://www.w3.org/2000/svg" width="52" height="36"><rect width="52" height="36" rx="4" fill="#1e293b"/><rect x="6" y="8" width="38" height="18" rx="3" fill="none" stroke="#22d3ee" stroke-width="1.8"/><circle cx="14" cy="27" r="4" stroke="#22d3ee" stroke-width="1.8"/><circle cx="36" cy="27" r="4" stroke="#22d3ee" stroke-width="1.8"/></svg>`,
    Car: `<svg viewBox="0 0 52 36" fill="none" xmlns="http://www.w3.org/2000/svg" width="52" height="36"><rect width="52" height="36" rx="4" fill="#1e293b"/><path d="M6 22L12 14H36L42 22V26H6V22Z" stroke="#38bdf8" stroke-width="1.8"/><circle cx="14" cy="27" r="4" stroke="#38bdf8" stroke-width="1.8"/><circle cx="36" cy="27" r="4" stroke="#38bdf8" stroke-width="1.8"/></svg>`,
    SUV: `<svg viewBox="0 0 52 36" fill="none" xmlns="http://www.w3.org/2000/svg" width="52" height="36"><rect width="52" height="36" rx="4" fill="#1e293b"/><path d="M4 22L10 11H36L44 22V26H4V22Z" stroke="#60a5fa" stroke-width="1.8"/><circle cx="14" cy="27" r="4.5" stroke="#60a5fa" stroke-width="1.8"/><circle cx="36" cy="27" r="4.5" stroke="#60a5fa" stroke-width="1.8"/></svg>`,
    Pickup: `<svg viewBox="0 0 52 36" fill="none" xmlns="http://www.w3.org/2000/svg" width="52" height="36"><rect width="52" height="36" rx="4" fill="#1e293b"/><path d="M4 22L12 12H28V22M28 17H46V22H4V26" stroke="#fbbf24" stroke-width="1.8"/><circle cx="14" cy="27" r="4" stroke="#fbbf24" stroke-width="1.8"/><circle cx="38" cy="27" r="4" stroke="#fbbf24" stroke-width="1.8"/></svg>`,
    Microbus: `<svg viewBox="0 0 52 36" fill="none" xmlns="http://www.w3.org/2000/svg" width="52" height="36"><rect width="52" height="36" rx="4" fill="#1e293b"/><rect x="6" y="8" width="40" height="18" rx="3" fill="none" stroke="#a78bfa" stroke-width="1.8"/><circle cx="14" cy="27" r="4" stroke="#a78bfa" stroke-width="1.8"/><circle cx="36" cy="27" r="4" stroke="#a78bfa" stroke-width="1.8"/></svg>`,
    Bus: `<svg viewBox="0 0 52 36" fill="none" xmlns="http://www.w3.org/2000/svg" width="52" height="36"><rect width="52" height="36" rx="4" fill="#1e293b"/><rect x="4" y="6" width="44" height="20" rx="3" fill="none" stroke="#60a5fa" stroke-width="1.8"/><circle cx="14" cy="28" r="4.5" stroke="#60a5fa" stroke-width="1.8"/><circle cx="38" cy="28" r="4.5" stroke="#60a5fa" stroke-width="1.8"/></svg>`,
    Truck: `<svg viewBox="0 0 52 36" fill="none" xmlns="http://www.w3.org/2000/svg" width="52" height="36"><rect width="52" height="36" rx="4" fill="#1e293b"/><rect x="4" y="10" width="28" height="16" rx="2" fill="none" stroke="#f87171" stroke-width="1.8"/><circle cx="12" cy="28" r="4" stroke="#f87171" stroke-width="1.5"/><circle cx="38" cy="28" r="4" stroke="#f87171" stroke-width="1.5"/></svg>`
  };

  const MAX_ROWS = 60;
  let currentRecords = [];
  let filterStatus = 'all';
  let filterSearch = '';

  function getVehicleSVG(type) {
    return VEHICLE_SVGS[type] || VEHICLE_SVGS['Car'];
  }

  function formatTime(val) {
    if (!val || val === 'Parked Inside' || val === '—') return val;
    try {
      const dt = new Date(val);
      if (!isNaN(dt.getTime())) {
        return dt.toLocaleTimeString('en-BD', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true });
      }
    } catch (e) {}
    return String(val);
  }

  function buildRow(record, isNew = false) {
    const isParked = (record.status === 'PARKED');
    const tr = document.createElement('tr');
    if (isNew) tr.classList.add('new-row');

    const hasImage = Boolean(record.image_path);
    let imgHtml = getVehicleSVG(record.vehicle_type);
    if (hasImage) {
      const cleanPath = record.image_path.startsWith('/') ? record.image_path : '/' + record.image_path;
      imgHtml = `<img src="${cleanPath}" style="width:100%;height:100%;object-fit:cover;display:block;" onerror="this.parentElement.innerHTML='${getVehicleSVG(record.vehicle_type).replace(/"/g, '&quot;')}'" />`;
    }

    const entryTimeFormatted = formatTime(record.entry_time);
    const exitTimeFormatted = isParked ? '<span style="color:#10b981;font-weight:600;font-size:11px;"><span class="cam-live-dot" style="display:inline-block;width:6px;height:6px;margin-right:4px;"></span>Parked Inside</span>' : formatTime(record.exit_time);

    const durStyle = isParked ? 'color:#38bdf8;font-weight:700;' : 'color:#94a3b8;font-weight:600;';
    const statusBadge = isParked
      ? `<span class="badge" style="background:rgba(16,185,129,0.15);color:#34d399;border:1px solid rgba(16,185,129,0.3);font-size:11px;padding:3px 8px;">PARKED</span>`
      : `<span class="badge" style="background:rgba(148,163,184,0.12);color:#cbd5e1;border:1px solid rgba(148,163,184,0.2);font-size:11px;padding:3px 8px;">EXITED</span>`;

    const gateSlot = record.slot_number ? `<span style="color:#60a5fa;font-weight:600;">Slot ${record.slot_number}</span>` : `<span style="color:#94a3b8;">${record.entry_gate || 'Gate 1'}</span>`;

    const feeVal = record.toll_amount != null ? record.toll_amount : (record.fee != null ? record.fee : 0);
    const feeHtml = `<td class="fee-col" style="font-family:monospace;font-size:12px;font-weight:600;color:#fbbf24;">৳ ${Number(feeVal).toLocaleString('en-BD')}</td>`;

    tr.innerHTML = `
      <td>
        <div style="width:52px;height:36px;border-radius:5px;overflow:hidden;border:1px solid rgba(255,255,255,0.1);display:flex;align-items:center;justify-content:center;background:#1e293b;">
          ${imgHtml}
        </div>
      </td>
      <td>
        <span class="badge" style="background:rgba(59,130,246,0.15);color:#60a5fa;border:1px solid rgba(59,130,246,0.3);font-weight:600;">
          ${record.vehicle_type}
        </span>
      </td>
      <td>
        <span class="bd-plate-badge" style="font-size:12px;padding:3px 8px;">
          <i class="bi bi-card-text me-1"></i>${record.plate_number}
        </span>
      </td>
      <td style="color:#cbd5e1;font-size:12px;font-family:monospace;">${entryTimeFormatted}</td>
      <td style="color:#cbd5e1;font-size:12px;font-family:monospace;">${exitTimeFormatted}</td>
      <td style="${durStyle}font-family:monospace;font-size:12px;">${record.duration_str || '—'}</td>
      <td style="font-size:12px;">${gateSlot}</td>
      <td>${statusBadge}</td>
      ${feeHtml}
    `;

    return tr;
  }

  async function loadRecords() {
    try {
      let url = '/api/detections?limit=60';
      if (filterStatus && filterStatus !== 'all') {
        url += `&status=${encodeURIComponent(filterStatus)}`;
      }
      if (filterSearch) {
        url += `&search=${encodeURIComponent(filterSearch)}`;
      }

      const res = await fetch(url);
      if (res.ok) {
        currentRecords = await res.json();
        renderTable();
      }
    } catch (e) {
      console.warn('Could not load parking detections', e);
    }
  }

  function renderTable() {
    const tbody = document.getElementById('detection-tbody');
    const badge = document.getElementById('live-count-badge');
    if (!tbody) return;

    tbody.innerHTML = '';

    if (!currentRecords || currentRecords.length === 0) {
      tbody.innerHTML = `<tr><td colspan="9" class="text-center py-4" style="color:#94a3b8;">No matching parking records found</td></tr>`;
      if (badge) badge.textContent = '0 movements';
      return;
    }

    if (badge) {
      const insideCount = currentRecords.filter(r => r.status === 'PARKED').length;
      badge.textContent = `${insideCount} currently inside · ${currentRecords.length} total logged`;
    }

    currentRecords.forEach(r => {
      tbody.appendChild(buildRow(r, false));
    });
  }

  function setStatusFilter(status) {
    filterStatus = (status || 'all').toLowerCase();
    
    // Toggle active classes on UI buttons
    const btnAll = document.getElementById('filter-btn-all');
    const btnParked = document.getElementById('filter-btn-parked');
    const btnExited = document.getElementById('filter-btn-exited');

    if (btnAll) btnAll.classList.toggle('active', filterStatus === 'all');
    if (btnParked) btnParked.classList.toggle('active', filterStatus === 'parked');
    if (btnExited) btnExited.classList.toggle('active', filterStatus === 'exited');

    loadRecords();
  }

  function filterBy(status) {
    setStatusFilter(status);
  }

  function filterByPlate(query) {
    filterSearch = (query || '').trim();
    loadRecords();
  }

  function search(query) {
    filterByPlate(query);
  }

  async function clearDetectionLogs() {
    if (!confirm('Are you sure you want to clear all parking movement records from the database?')) {
      return;
    }
    try {
      const res = await fetch('/api/detections', { method: 'DELETE' });
      const data = await res.json().catch(() => ({}));
      if (res.ok) {
        currentRecords = [];
        renderTable();
        const searchInput = document.getElementById('plate-search-input');
        if (searchInput) searchInput.value = '';
        filterSearch = '';
        if (window.App && window.App.toast) {
          window.App.toast('All parking movement records cleared successfully', 'success');
        }
        if (window.Dashboard && window.Dashboard.loadParkingStats) {
          window.Dashboard.loadParkingStats();
        }
      } else {
        if (window.App && window.App.toast) {
          window.App.toast(data.message || 'Failed to clear parking logs', 'error');
        }
      }
    } catch (err) {
      console.error('Error clearing detection records:', err);
      if (window.App && window.App.toast) {
        window.App.toast('Network error while clearing logs', 'error');
      }
    }
  }

  function init() {
    loadRecords();

    // Attach search input listener if present
    const searchInput = document.getElementById('plate-search-input');
    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        filterByPlate(e.target.value);
      });
    }

    // Periodic refresh every 3 seconds
    setInterval(() => {
      loadRecords();
    }, 3000);
  }

  return {
    init,
    loadRecords,
    filterBy,
    setStatusFilter,
    search,
    filterByPlate,
    clearDetectionLogs,
    insertRow(record) {
      currentRecords.unshift(record);
      renderTable();
    }
  };
})();

// Global exports for inline HTML onclick handlers
window.DetectionTable = DetectionTable;
window.DetectionTableModule = DetectionTable;
window.clearDetectionLogs = () => DetectionTable.clearDetectionLogs();

