// Tariff and fee rates management

const RatesModule = (() => {

  // Default vehicle list with empty rates by default as requested
  const DEFAULT_VEHICLES = [
    { type: 'Bike', name: 'Motorcycle & Two-Wheeler', icon: 'bi-bicycle', defaultRate: '' },
    { type: 'CNG', name: 'Auto-Rickshaw (3-Wheeler)', icon: 'bi-shield-shaded', defaultRate: '' },
    { type: 'Car', name: 'Sedan, Hatchback & Taxi', icon: 'bi-car-front-fill', defaultRate: '' },
    { type: 'SUV', name: 'SUV, Jeep & Crossover', icon: 'bi-truck-flatbed', defaultRate: '' },
    { type: 'Microbus', name: 'Minivan, HiAce & Passenger Van', icon: 'bi-bus-front-fill', defaultRate: '' },
    { type: 'Pickup', name: 'Light Pickup Transport', icon: 'bi-truck', defaultRate: '' },
    { type: 'Bus', name: 'City Bus & Inter-District Coach', icon: 'bi-bus-front', defaultRate: '' },
    { type: 'Truck', name: 'Heavy Commercial Cargo Truck', icon: 'bi-box-seam-fill', defaultRate: '' },
    { type: 'Trailer', name: 'Multi-Axle Heavy Carrier', icon: 'bi-train-front', defaultRate: '' }
  ];

  function getSavedTariffs() {
    try {
      const stored = localStorage.getItem('smartpark_custom_tariffs');
      if (stored) {
        return JSON.parse(stored);
      }
    } catch (e) {
      console.warn('Error reading tariffs from localStorage', e);
    }
    // Return empty dictionary by default
    return {};
  }

  function saveTariffsToStorage(tariffs) {
    try {
      localStorage.setItem('smartpark_custom_tariffs', JSON.stringify(tariffs));
      window.AppCustomTariffs = tariffs;
    } catch (e) {
      console.error('Error saving tariffs to localStorage', e);
    }
  }

  function showToast(msg, type = 'success') {
    if (window.App && typeof window.App.toast === 'function') {
      window.App.toast(msg, type);
      return;
    }
    const container = document.getElementById('toast-container');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = `toast-msg ${type}`;
    toast.innerHTML = `
      <i class="bi bi-${type === 'success' ? 'check-circle-fill' : 'exclamation-circle-fill'}" style="color:var(--${type === 'success' ? 'success' : 'danger'});font-size:18px;"></i>
      <span>${msg}</span>`;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 3500);
  }

  function renderTable() {
    const tbody = document.getElementById('tariffs-table-body');
    if (!tbody) return;

    const saved = getSavedTariffs();
    window.AppCustomTariffs = saved;

    tbody.innerHTML = DEFAULT_VEHICLES.map((v, idx) => {
      const val = saved[v.type] != null ? saved[v.type] : '';
      const hasRate = (val !== '' && val !== null && !isNaN(val) && Number(val) > 0);

      const statusBadge = hasRate
        ? `<span class="badge bg-success-subtle text-success border border-success-subtle px-2 py-1"><i class="bi bi-check2"></i> ৳ ${val} Set</span>`
        : `<span class="badge bg-secondary-subtle text-secondary border border-secondary-subtle px-2 py-1"><i class="bi bi-dash-circle"></i> Empty / Not Set</span>`;

      return `
        <tr class="align-middle">
          <td style="width: 45px; text-align: center;">
            <div class="vehicle-icon-box" style="width:36px;height:36px;border-radius:8px;background:rgba(59,130,246,0.1);display:inline-flex;align-items:center;justify-content:center;color:#60a5fa;font-size:16px;">
              <i class="bi ${v.icon}"></i>
            </div>
          </td>
          <td>
            <div style="font-weight: 600; color: var(--text-primary);">${v.type}</div>
            <div style="font-size: 11px; color: var(--text-muted);">${v.name}</div>
          </td>
          <td style="width: 220px;">
            <div class="input-group input-group-sm">
              <span class="input-group-text" style="background: rgba(255,255,255,0.04); border-color: var(--border); color: var(--text-secondary);">৳</span>
              <input 
                type="number" 
                class="form-control form-control-sm rate-input" 
                id="rate-input-${v.type}"
                placeholder="Manual fee..." 
                value="${val}" 
                min="0" 
                step="5"
                style="background: rgba(255,255,255,0.06); border-color: var(--border); color: #fff; font-family: var(--font-mono); font-weight: 600;"
              />
            </div>
          </td>
          <td>
            ${statusBadge}
          </td>
          <td class="text-end" style="width: 140px;">
            <button class="btn btn-sm btn-outline-primary me-1" onclick="RatesModule.saveSingleRate('${v.type}')" title="Save this fee" style="padding: 4px 10px; font-size: 11px; border-radius: 6px;">
              <i class="bi bi-check-lg"></i> Apply
            </button>
            <button class="btn btn-sm btn-outline-secondary" onclick="RatesModule.clearSingleRate('${v.type}')" title="Clear / Empty fee" style="padding: 4px 8px; font-size: 11px; border-radius: 6px;">
              <i class="bi bi-x-lg"></i>
            </button>
          </td>
        </tr>
      `;
    }).join('');

    updateSummaryBanner(saved);
  }

  function updateSummaryBanner(saved) {
    const bannerEl = document.getElementById('tariffs-summary-text');
    if (!bannerEl) return;

    const countSet = Object.values(saved).filter(v => v !== '' && v !== null && !isNaN(v) && Number(v) > 0).length;
    if (countSet === 0) {
      bannerEl.innerHTML = `<span class="badge bg-warning-subtle text-warning me-2"><i class="bi bi-pencil-square"></i> Manual Mode Active</span> All rates are currently empty. Enter fees manually as needed or leave blank.`;
    } else {
      bannerEl.innerHTML = `<span class="badge bg-success-subtle text-success me-2"><i class="bi bi-check-circle-fill"></i> ${countSet} Rates Configured</span> Custom fees active for ${countSet} vehicle categories.`;
    }
  }

  function saveSingleRate(vtype) {
    const input = document.getElementById(`rate-input-${vtype}`);
    if (!input) return;
    const val = input.value.trim();

    const tariffs = getSavedTariffs();
    if (val === '') {
      delete tariffs[vtype];
      saveTariffsToStorage(tariffs);
      showToast(`${vtype} fee set to Empty / Free`, 'info');
    } else {
      tariffs[vtype] = Number(val);
      saveTariffsToStorage(tariffs);
      showToast(`Updated ${vtype} rate to ৳ ${val}`, 'success');
    }
    renderTable();
  }

  function clearSingleRate(vtype) {
    const input = document.getElementById(`rate-input-${vtype}`);
    if (input) input.value = '';
    const tariffs = getSavedTariffs();
    delete tariffs[vtype];
    saveTariffsToStorage(tariffs);
    showToast(`Cleared ${vtype} fee`, 'info');
    renderTable();
  }

  function saveAllRates() {
    const tariffs = getSavedTariffs();
    DEFAULT_VEHICLES.forEach(v => {
      const input = document.getElementById(`rate-input-${v.type}`);
      if (input) {
        const val = input.value.trim();
        if (val === '' || isNaN(val)) {
          delete tariffs[v.type];
        } else {
          tariffs[v.type] = Number(val);
        }
      }
    });

    saveTariffsToStorage(tariffs);
    showToast('All custom tariff rates successfully saved!', 'success');
    renderTable();
  }

  function clearAllRates() {
    if (!confirm('Are you sure you want to clear all fee entries and set them to empty?')) {
      return;
    }
    saveTariffsToStorage({});
    DEFAULT_VEHICLES.forEach(v => {
      const input = document.getElementById(`rate-input-${v.type}`);
      if (input) input.value = '';
    });
    showToast('All fees reset to empty (Manual / Free Access Mode)', 'info');
    renderTable();
  }

  function addCustomCategory() {
    const catName = prompt('Enter new custom vehicle or category name (e.g., Ambulance, VIP Escort, Electric Scooter):');
    if (!catName || !catName.trim()) return;

    const trimmed = catName.trim();
    const rateStr = prompt(`Enter manual fee amount for "${trimmed}" in BDT (leave blank if 0 / Free):`, '');
    const rateVal = rateStr && !isNaN(rateStr.trim()) ? Number(rateStr.trim()) : '';

    const tariffs = getSavedTariffs();
    tariffs[trimmed] = rateVal;
    saveTariffsToStorage(tariffs);

    DEFAULT_VEHICLES.push({
      type: trimmed,
      name: `${trimmed} (Custom Category)`,
      icon: 'bi-tag-fill',
      defaultRate: rateVal
    });

    showToast(`Added custom category: ${trimmed}`, 'success');
    renderTable();
  }

  return {
    init() {
      renderTable();
    },
    renderTable,
    saveSingleRate,
    clearSingleRate,
    saveAllRates,
    clearAllRates,
    addCustomCategory,
    getTariffForType(type) {
      const tariffs = getSavedTariffs();
      if (tariffs[type] != null && tariffs[type] !== '') {
        return tariffs[type];
      }
      return null;
    }
  };
})();

window.RatesModule = RatesModule;

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  RatesModule.init();
});
