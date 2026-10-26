// Overstay and security alerts

const FraudModule = (() => {

  function renderOverstayTable(overstayData) {
    const container = document.getElementById('fraud-comparison-table');
    if (!container) return;

    const data = overstayData?.data || {
      Car:    { parked: 14, exited: 32, overstay: 1 },
      Bike:   { parked: 8,  exited: 20, overstay: 0 },
      CNG:    { parked: 4,  exited: 10, overstay: 1 },
      Auto:   { parked: 2,  exited: 4,  overstay: 0 },
      Pickup: { parked: 1,  exited: 3,  overstay: 1 },
      Bus:    { parked: 1,  exited: 1,  overstay: 0 }
    };

    let totalParked = 0, totalExited = 0, totalOverstay = 0;

    const rows = Object.entries(data).map(([type, d]) => {
      totalParked += (d.parked || 0);
      totalExited += (d.exited || 0);
      totalOverstay += (d.overstay || 0);

      const emoji = (window.AppData && window.AppData.VEHICLE_EMOJIS && window.AppData.VEHICLE_EMOJIS[type]) || '🚗';
      const typeClass = (window.AppData && window.AppData.VEHICLE_COLORS && window.AppData.VEHICLE_COLORS[type]) || '';

      const hasAlert = d.overstay > 0;

      return `
      <div class="fraud-row">
        <div class="vehicle-name">
          <span class="type-badge ${typeClass}" style="font-size:12px;">${emoji} ${type}</span>
        </div>
        <div class="operator-count" style="font-size:13px; color:#38bdf8; font-weight:600;">${(d.parked || 0).toLocaleString()} inside</div>
        <div class="ai-count" style="font-size:13px; color:#94a3b8;">${(d.exited || 0).toLocaleString()} exited</div>
        <div class="discrepancy">
          ${hasAlert
            ? `<span class="discrepancy-badge" style="background:rgba(239,68,68,0.18); color:#f87171; border:1px solid rgba(239,68,68,0.3);"><i class="bi bi-clock-history me-1"></i>${d.overstay} Overstay (>12h)</span>`
            : `<span class="discrepancy-badge ok"><i class="bi bi-check2 me-1"></i>Normal Duration</span>`}
        </div>
      </div>`;
    }).join('');

    container.innerHTML = `
      <div class="fraud-comparison-card">
        <div class="fc-header">
          <span>Category</span>
          <span>Currently Parked</span>
          <span>Today's Departures</span>
          <span>Duration Status</span>
        </div>
        ${rows}
        <div class="fraud-row" style="background:rgba(59,130,246,0.06);border-top:1px solid rgba(59,130,246,0.2);margin-top:4px;">
          <div class="vehicle-name" style="color:var(--text-primary);font-weight:700;">TOTAL MOVEMENTS</div>
          <div style="font-weight:700;color:#38bdf8;">${totalParked.toLocaleString()} inside</div>
          <div style="font-weight:700;color:#94a3b8;">${totalExited.toLocaleString()} exited</div>
          <div>
            ${totalOverstay > 0 
              ? `<span class="discrepancy-badge" style="background:rgba(239,68,68,0.2);color:#f87171;">⚠️ ${totalOverstay} Total Overstays</span>` 
              : `<span class="discrepancy-badge ok">✓ All Within Limit</span>`}
          </div>
        </div>
      </div>`;

    updateSummaryCards(totalOverstay, totalExited, totalParked);
  }

  function updateSummaryCards(overstayCount, exitedCount, parkedCount) {
    const elOverstay = document.getElementById('fraud-leakage-amount');
    const elOccupancy = document.getElementById('fraud-leakage-pct');
    const elExited = document.getElementById('fraud-operator-total');
    const elParked = document.getElementById('fraud-ai-total');

    const totalCapacity = 150;
    const occupancyPct = Math.min(100, Math.round((parkedCount / totalCapacity) * 100));

    if (elOverstay) elOverstay.textContent = `${overstayCount} Vehicles`;
    if (elOccupancy) elOccupancy.textContent = `${occupancyPct}%`;
    if (elExited) elExited.textContent = exitedCount.toLocaleString();
    if (elParked) elParked.textContent = parkedCount.toLocaleString();
  }

  function renderAlertBanner(overstayCount) {
    const banner = document.getElementById('fraud-alert-banner');
    if (!banner) return;

    if (overstayCount > 0) {
      banner.innerHTML = `
        <div class="alert-icon">⏱️</div>
        <div>
          <h5>⚠️ Active Overstay Alert (${overstayCount} Vehicles Exceeded Limit)</h5>
          <p>AI tracking detected <strong style="color:#f87171;">${overstayCount} vehicles</strong> continuously parked for over 12 hours without exit verification. Review active bay cameras.</p>
        </div>
        <div style="margin-left:auto;text-align:right;flex-shrink:0;">
          <div style="font-size:22px;font-weight:800;color:#f87171;">${overstayCount}</div>
          <div style="font-size:11px;color:var(--text-muted);">Overstay Alerts</div>
        </div>`;
    } else {
      banner.style.border = '1px solid rgba(16,185,129,0.3)';
      banner.style.background = 'rgba(16,185,129,0.08)';
      banner.innerHTML = `
        <div class="alert-icon" style="color:#34d399;">✓</div>
        <div>
          <h5 style="color:#34d399;">All Parked Vehicles Within Safe Duration Limits</h5>
          <p style="color:var(--text-secondary);">No vehicles have exceeded the maximum 12-hour continuous stay threshold. Normal facility operations.</p>
        </div>`;
    }
  }

  return {
    async init() {
      let overstayData = null;
      if (window.AppData && window.AppData.isBackend) {
        try {
          const resp = await fetch('/api/fraud');
          if (resp.ok) {
            overstayData = await resp.json();
          }
        } catch (e) {
          console.error('[Overstay] Error fetching data:', e);
        }
      }

      const totalOverstay = overstayData?.overstay_count || 3;
      renderAlertBanner(totalOverstay);
      renderOverstayTable(overstayData);
    }
  };
})();

window.FraudModule = FraudModule;
