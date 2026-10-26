// Dashboard statistics and live counters

const Dashboard = (() => {

  // Animated numeric counter helper
  function animateCounter(el, target, duration = 1500, prefix = '', suffix = '') {
    const start = 0;
    const startTime = performance.now();

    function update(currentTime) {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = Math.round(start + (target - start) * eased);
      el.textContent = prefix + current.toLocaleString('en-BD') + suffix;
      if (progress < 1) requestAnimationFrame(update);
    }
    requestAnimationFrame(update);
  }

  // Stat cards renderer
  function renderStatCards() {
    const p = (window.AppData && window.AppData.parkingStats) || {};
    const d = window.AppData || {};

    const currentlyParked = p.currently_parked != null ? p.currently_parked : (d.records ? d.records.filter(r => r.status === 'PARKED').length : 30);
    const totalCapacity = p.total_capacity || 150;
    const availableSlots = p.available_slots != null ? p.available_slots : Math.max(0, totalCapacity - currentlyParked);
    const todayEntries = p.today_entries != null ? p.today_entries : (d.records ? d.records.length : 100);
    const todayExits = p.today_exits != null ? p.today_exits : 70;
    const avgStay = p.avg_duration_str || "4h 28m";
    const overstay = p.overstay_alerts || 0;
    const occupancyPct = p.occupancy_pct != null ? p.occupancy_pct : Math.round((currentlyParked / totalCapacity) * 100);

    const cards = [
      {
        id: 'stat-currently-parked',
        label: 'Currently Parked',
        value: currentlyParked,
        suffix: ` / ${totalCapacity}`,
        icon: 'bi-p-square-fill',
        color: '#38bdf8',
        iconBg: 'rgba(56,189,248,0.15)',
        change: `${occupancyPct}% Full`,
        changeDir: 'up',
        changeLabel: 'Occupancy'
      },
      {
        id: 'stat-available-slots',
        label: 'Available Free Slots',
        value: availableSlots,
        suffix: ' Slots',
        icon: 'bi-check-circle-fill',
        color: '#34d399',
        iconBg: 'rgba(52,211,153,0.15)',
        change: `${totalCapacity - currentlyParked} Free`,
        changeDir: 'up',
        changeLabel: 'Bays'
      },
      {
        id: 'stat-today-entries',
        label: "Today's Total Entries",
        value: todayEntries,
        suffix: ' Cars',
        icon: 'bi-box-arrow-in-right',
        color: '#818cf8',
        iconBg: 'rgba(129,140,248,0.15)',
        change: 'Gate 1 Inbound',
        changeDir: 'up',
        changeLabel: ''
      },
      {
        id: 'stat-today-exits',
        label: "Today's Completed Exits",
        value: todayExits,
        suffix: ' Cars',
        icon: 'bi-box-arrow-right',
        color: '#f59e0b',
        iconBg: 'rgba(245,158,11,0.15)',
        change: 'Gate 2 Outbound',
        changeDir: 'up',
        changeLabel: ''
      },
      {
        id: 'stat-avg-duration',
        label: 'Average Stay Duration',
        valueStr: avgStay,
        icon: 'bi-clock-history',
        color: '#c084fc',
        iconBg: 'rgba(192,132,252,0.15)',
        change: 'Per completed visit',
        changeDir: 'up',
        changeLabel: ''
      },
      {
        id: 'stat-overstay',
        label: 'Overstay Alerts (>12h)',
        value: overstay,
        suffix: ' Alerts',
        icon: 'bi-exclamation-triangle-fill',
        color: overstay > 0 ? '#f87171' : '#34d399',
        iconBg: overstay > 0 ? 'rgba(248,113,113,0.15)' : 'rgba(52,211,153,0.15)',
        change: overstay > 0 ? 'NEEDS ATTENTION' : 'All Clear',
        changeDir: overstay > 0 ? 'down' : 'up',
        changeLabel: ''
      }
    ];

    const container = document.getElementById('stat-cards-row');
    if (!container) return;

    container.innerHTML = '';

    cards.forEach(card => {
      const col = document.createElement('div');
      col.className = 'col-xl-2 col-lg-4 col-md-4 col-sm-6 mb-3';

      col.innerHTML = `
        <div class="stat-card" style="--stat-color:${card.color}; --stat-icon-bg:${card.iconBg};">
          <div class="stat-info">
            <div class="stat-label">${card.label}</div>
            <div class="stat-value" id="${card.id}">${card.valueStr || 0}</div>
            <div class="stat-change ${card.changeDir}">
              <i class="bi bi-arrow-${card.changeDir === 'up' ? 'up-right' : 'down-right'}"></i>
              <span>${card.change}</span>
              <span style="color:var(--text-muted)">${card.changeLabel}</span>
            </div>
          </div>
          <div class="stat-icon">
            <i class="bi ${card.icon}"></i>
          </div>
          <div class="stat-glow"></div>
        </div>`;
      container.appendChild(col);

      // Animate after a short delay
      setTimeout(() => {
        const el = document.getElementById(card.id);
        if (el) {
          if (card.valueStr) {
            el.textContent = card.valueStr;
          } else {
            animateCounter(el, card.value, 1500, card.prefix || '', card.suffix || '');
          }
        }
      }, 150);
    });
  }

  // Live periodic statistic polling
  function startLiveUpdates() {
    setInterval(async () => {
      try {
        const resp = await fetch('/api/stats');
        if (resp.ok) {
          const stats = await resp.json();
          window.AppData.parkingStats = stats;
          
          const elParked = document.getElementById('stat-currently-parked');
          const elFree = document.getElementById('stat-available-slots');
          const elEntries = document.getElementById('stat-today-entries');
          const elExits = document.getElementById('stat-today-exits');
          const elDuration = document.getElementById('stat-avg-duration');
          const elAlerts = document.getElementById('stat-overstay');

          if (elParked) elParked.textContent = `${stats.currently_parked} / ${stats.total_capacity}`;
          if (elFree) elFree.textContent = `${stats.available_slots} Slots`;
          if (elEntries) elEntries.textContent = `${stats.today_entries} Cars`;
          if (elExits) elExits.textContent = `${stats.today_exits} Cars`;
          if (elDuration) elDuration.textContent = stats.avg_duration_str || '—';
          if (elAlerts) elAlerts.textContent = `${stats.overstay_alerts} Alerts`;
        }
      } catch (err) {}
    }, 6000);
  }

  return {
    async init() {
      try {
        const res = await fetch('/api/stats');
        if (res.ok) {
          window.AppData.parkingStats = await res.json();
        }
      } catch (e) {}

      renderStatCards();
      startLiveUpdates();
    },

    refresh() {
      renderStatCards();
    }
  };
})();

window.Dashboard = Dashboard;
