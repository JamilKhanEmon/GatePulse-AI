// Reports generation & export

const ReportsModule = (() => {

  let currentType = 'daily';
  let selectedSlot = 'slot2'; // Default to Evening Shift (14:00 - 22:00 / 2 PM - 10 PM)
  let selectedDate = new Date().toISOString().slice(0, 10);
  let startTime = '14:00';
  let endTime = '22:00';
  let dynamicReportLabel = '';

  const SLOT_NAMES = {
    slot1: 'Slot 1: Morning Shift (06:00 AM – 02:00 PM)',
    slot2: 'Slot 2: Evening Shift (02:00 PM – 10:00 PM)',
    slot3: 'Slot 3: Night Shift (10:00 PM – 06:00 AM)',
    custom: 'Custom Time Slot'
  };

  function getWeekLabel() {
    const now = new Date();
    const start = new Date(now);
    start.setDate(now.getDate() - now.getDay());
    const end = new Date(start);
    end.setDate(start.getDate() + 6);
    return `${start.toLocaleDateString('en-BD', { day: '2-digit', month: 'short' })} – ${end.toLocaleDateString('en-BD', { day: '2-digit', month: 'short', year: 'numeric' })}`;
  }

  function getReportTitle() {
    if (dynamicReportLabel) return dynamicReportLabel;
    if (currentType === 'slot') {
      const slotName = SLOT_NAMES[selectedSlot] || '8-Hour Shift Slot';
      if (selectedSlot === 'custom') {
        return `Custom Slot (${startTime} – ${endTime}) · ${selectedDate}`;
      }
      return `${slotName} · ${selectedDate}`;
    }
    if (currentType === 'weekly') {
      return 'Weekly Report — ' + getWeekLabel();
    }
    if (currentType === 'monthly') {
      return 'Monthly Report — ' + new Date().toLocaleDateString('en-BD', { year: 'numeric', month: 'long' });
    }
    return 'Daily Report — ' + (selectedDate ? new Date(selectedDate + 'T00:00:00').toLocaleDateString('en-BD', { year: 'numeric', month: 'long', day: 'numeric' }) : new Date().toLocaleDateString('en-BD', { year: 'numeric', month: 'long', day: 'numeric' }));
  }

  async function getReportData(type) {
    if (window.AppData && window.AppData.isBackend) {
      try {
        let url = `/api/reports?type=${type}&date=${selectedDate}`;
        if (type === 'slot') {
          url += `&slot=${selectedSlot}&start_time=${startTime}&end_time=${endTime}`;
        }
        const resp = await fetch(url);
        if (resp.ok) {
          const data = await resp.json();
          if (data.label) dynamicReportLabel = data.label;
          return {
            rows: data.rows || [],
            totalCount: data.totalCount || 0,
            totalRevenue: data.totalRevenue || 0,
            multiplier: 1
          };
        }
      } catch (e) {
        console.error('[Reports] Error loading report data:', e);
      }
    }

    // Client-side fallback computation
    const d = window.AppData || {};
    const rev = (d.revenue && d.revenue.byType) ? d.revenue.byType : {};
    let multiplier = 1;
    if (type === 'slot') multiplier = 0.35; // 8-hour shift is ~35% of daily total
    else if (type === 'weekly') multiplier = 7;
    else if (type === 'monthly') multiplier = 30;

    const rows = Object.entries(rev)
      .filter(([, v]) => v.count > 0)
      .map(([vehicleType, v]) => ({
        vehicle_type: vehicleType,
        count: Math.max(1, Math.round(v.count * multiplier)),
        rate: (d.VEHICLE_RATES && d.VEHICLE_RATES[vehicleType]) || 20,
        revenue: Math.round(v.revenue * multiplier)
      }));

    const totalCount = rows.reduce((s, r) => s + r.count, 0);
    const totalRevenue = rows.reduce((s, r) => s + r.revenue, 0);

    return { rows, totalCount, totalRevenue, multiplier };
  }

  async function renderReportTable() {
    const container = document.getElementById('report-table-container');
    const titleEl = document.getElementById('report-title');
    const summaryContainer = document.getElementById('report-summary');
    if (!container) return;

    const { rows, totalCount } = await getReportData(currentType);
    const d = window.AppData || {};

    if (titleEl) titleEl.textContent = getReportTitle();

    const insideEst = Math.round(totalCount * 0.3);
    const exitedEst = totalCount - insideEst;

    // Summary cards
    if (summaryContainer) {
      summaryContainer.innerHTML = `
        <div class="col-md-4">
          <div class="summary-stat">
            <div class="s-value text-primary-c">${totalCount.toLocaleString()}</div>
            <div class="s-label">Total Vehicles Logged</div>
          </div>
        </div>
        <div class="col-md-4">
          <div class="summary-stat">
            <div class="s-value text-success-c">${insideEst.toLocaleString()}</div>
            <div class="s-label">Estimated Currently Inside</div>
          </div>
        </div>
        <div class="col-md-4">
          <div class="summary-stat">
            <div class="s-value" style="color:#fbbf24;">${exitedEst.toLocaleString()}</div>
            <div class="s-label">Completed Exits</div>
          </div>
        </div>`;
    }

    // Table
    const tableRows = rows.map((r, i) => `
      <tr>
        <td>${i + 1}</td>
        <td>
          <span class="type-badge ${(d.VEHICLE_COLORS && d.VEHICLE_COLORS[r.vehicle_type]) || 'type-car'}" style="font-size:12px;">
            ${(d.VEHICLE_EMOJIS && d.VEHICLE_EMOJIS[r.vehicle_type]) || '🚗'} ${r.vehicle_type}
          </span>
        </td>
        <td>${r.count.toLocaleString()}</td>
        <td style="color:#34d399;font-weight:600;">${Math.round(r.count * 0.3)} inside</td>
        <td style="color:#94a3b8;">${r.count - Math.round(r.count * 0.3)} exited</td>
        <td style="font-size:11px;color:var(--text-muted);">${totalCount > 0 ? ((r.count / totalCount) * 100).toFixed(1) : 0}%</td>
      </tr>`).join('');

    container.innerHTML = `
      <div class="detection-table-wrapper">
        <table class="detection-table" id="report-data-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Vehicle Type</th>
              <th>Total Logged</th>
              <th>Inside Facility</th>
              <th>Departed</th>
              <th>Share %</th>
            </tr>
          </thead>
          <tbody>
            ${tableRows || '<tr><td colspan="6" class="text-center py-4 text-muted">No parking movements logged for this period.</td></tr>'}
            <tr style="border-top:2px solid rgba(255,255,255,0.1);background:rgba(255,255,255,0.02);">
              <td colspan="2" style="font-weight:700;color:var(--text-primary);">GRAND TOTAL</td>
              <td style="font-weight:700;color:var(--text-primary);">${totalCount.toLocaleString()}</td>
              <td style="font-weight:700;color:#34d399;">${insideEst.toLocaleString()}</td>
              <td style="font-weight:700;color:#94a3b8;">${exitedEst.toLocaleString()}</td>
              <td style="font-weight:700;color:var(--text-primary);">100%</td>
            </tr>
          </tbody>
        </table>
      </div>`;
  }

  async function setReportType(type) {
    currentType = type;
    dynamicReportLabel = '';
    document.querySelectorAll('.report-tab').forEach(t => t.classList.remove('active'));
    const tab = document.getElementById(`tab-${type}`);
    if (tab) tab.classList.add('active');

    // Show / hide slot filter panel
    const filterPanel = document.getElementById('slot-filter-panel');
    if (filterPanel) {
      filterPanel.style.display = (type === 'daily' || type === 'slot') ? 'block' : 'none';
    }
    await renderReportTable();
  }

  function onSlotSelectChange(val) {
    selectedSlot = val;
    dynamicReportLabel = '';
    const customTimeGroup = document.getElementById('custom-time-group');
    if (customTimeGroup) {
      customTimeGroup.style.display = (val === 'custom') ? 'block' : 'none';
    }
    if (val === 'slot1') {
      startTime = '06:00';
      endTime = '14:00';
    } else if (val === 'slot2') {
      startTime = '14:00';
      endTime = '22:00';
    } else if (val === 'slot3') {
      startTime = '22:00';
      endTime = '06:00';
    }
  }

  async function applySlotFilter() {
    const dateInput = document.getElementById('report-date-input');
    const slotSelect = document.getElementById('report-slot-select');
    const startInput = document.getElementById('report-start-time');
    const endInput = document.getElementById('report-end-time');

    if (dateInput && dateInput.value) selectedDate = dateInput.value;
    if (slotSelect && slotSelect.value) selectedSlot = slotSelect.value;
    if (startInput && startInput.value) startTime = startInput.value;
    if (endInput && endInput.value) endTime = endInput.value;

    currentType = 'slot';
    dynamicReportLabel = '';
    document.querySelectorAll('.report-tab').forEach(t => t.classList.remove('active'));
    const tab = document.getElementById('tab-slot');
    if (tab) tab.classList.add('active');

    await renderReportTable();
    showToast(`Filtered report for ${getReportTitle()}`, 'success');
  }

  async function exportPDF() {
    if (typeof jspdf === 'undefined' && typeof window.jspdf === 'undefined') {
      showToast('PDF library loading... please try again.', 'error');
      return;
    }

    const { jsPDF } = window.jspdf;
    const doc = new jsPDF();
    const titleText = getReportTitle();

    // Header
    const facProfile = (window.App && window.App.getFacilityProfile) ? window.App.getFacilityProfile() : { name: 'GatePulse AI', subtitle: 'Smart Access & ANPR Vision' };
    const facHeader = `${facProfile.icon || '🚘'} ${facProfile.name} — Vehicle Movement Report`;

    doc.setFillColor(11, 17, 32);
    doc.rect(0, 0, 210, 40, 'F');
    doc.setTextColor(255, 255, 255);
    doc.setFontSize(15);
    doc.setFont(undefined, 'bold');
    doc.text(facHeader, 105, 15, { align: 'center' });
    doc.setFontSize(11);
    doc.setFont(undefined, 'normal');
    doc.text(titleText, 105, 25, { align: 'center' });
    doc.setFontSize(8.5);
    doc.text(`Generated: ${new Date().toLocaleString('en-BD')} | Facility: ${facProfile.name} | Officer: Admin Officer`, 105, 34, { align: 'center' });

    // Data
    const { rows, totalCount } = await getReportData(currentType);

    const insideEstTotal = Math.round(totalCount * 0.3);
    const exitedEstTotal = totalCount - insideEstTotal;

    const tableData = rows.map((r, i) => [
      i + 1,
      r.vehicle_type,
      r.count.toLocaleString(),
      Math.round(r.count * 0.3).toLocaleString(),
      (r.count - Math.round(r.count * 0.3)).toLocaleString(),
      `${totalCount > 0 ? ((r.count / totalCount) * 100).toFixed(1) : 0}%`
    ]);
    tableData.push(['', 'SHIFT / GRAND TOTAL', totalCount.toLocaleString(), insideEstTotal.toLocaleString(), exitedEstTotal.toLocaleString(), '100%']);

    doc.autoTable({
      startY: 48,
      head: [['#', 'Vehicle Category', 'Total Movements', 'Inside Facility', 'Exited Facility', 'Share %']],
      body: tableData,
      theme: 'grid',
      headStyles: { fillColor: [37, 99, 235], textColor: 255, fontStyle: 'bold', fontSize: 10 },
      bodyStyles: { fontSize: 9, textColor: [30, 30, 30] },
      alternateRowStyles: { fillColor: [245, 247, 250] },
      footStyles: { fontStyle: 'bold', fillColor: [240, 244, 255] },
      margin: { left: 14, right: 14 }
    });

    const finalY = doc.lastAutoTable.finalY + 10;
    doc.setFontSize(9);
    doc.setTextColor(100, 100, 100);
    doc.text('GatePulse AI · Official Vehicle Movement & Access Report', 105, finalY, { align: 'center' });

    const filename = `parking-report-${currentType}-${selectedDate || new Date().toISOString().slice(0,10)}.pdf`;
    doc.save(filename);
    showToast('📄 Parking PDF report exported successfully!', 'success');
  }

  async function exportExcel() {
    if (typeof XLSX === 'undefined') {
      showToast('Excel library loading... please try again.', 'error');
      return;
    }

    const { rows, totalCount } = await getReportData(currentType);
    const titleText = getReportTitle();
    const insideEstTotal = Math.round(totalCount * 0.3);
    const exitedEstTotal = totalCount - insideEstTotal;

    const facProfile = (window.App && window.App.getFacilityProfile) ? window.App.getFacilityProfile() : { name: 'GatePulse AI', subtitle: 'Smart Access & ANPR Vision' };
    const facHeader = `${facProfile.icon || '🚘'} ${facProfile.name} — Vehicle Movement Report`;

    const wsData = [
      [facHeader],
      [titleText],
      [`Generated: ${new Date().toLocaleString('en-BD')} | Facility: ${facProfile.name} | Shift: ${SLOT_NAMES[selectedSlot] || 'Custom'}`],
      [],
      ['#', 'Vehicle Category', 'Total Movements', 'Inside Facility', 'Exited Facility', 'Share %'],
      ...rows.map((r, i) => [
        i + 1, r.vehicle_type, r.count, Math.round(r.count * 0.3), (r.count - Math.round(r.count * 0.3)),
        parseFloat(totalCount > 0 ? ((r.count / totalCount) * 100).toFixed(1) : 0)
      ]),
      ['', 'GRAND TOTAL', totalCount, insideEstTotal, exitedEstTotal, 100],
      [],
      [`${facProfile.name} Monitoring · Official Vehicle Movement Log`]
    ];

    const ws = XLSX.utils.aoa_to_sheet(wsData);
    ws['!cols'] = [
      { wch: 4 }, { wch: 18 }, { wch: 16 }, { wch: 16 }, { wch: 16 }, { wch: 12 }
    ];

    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Parking Movement Report');
    const filename = `parking-report-${currentType}-${selectedDate || new Date().toISOString().slice(0,10)}.xlsx`;
    XLSX.writeFile(wb, filename);
    showToast('📊 Parking Excel report exported successfully!', 'success');
  }

  function showToast(msg, type = 'success') {
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

  function init() {
    const dateInput = document.getElementById('report-date-input');
    if (dateInput) {
      dateInput.value = selectedDate;
      dateInput.addEventListener('change', (e) => {
        selectedDate = e.target.value;
      });
    }
    const slotSelect = document.getElementById('report-slot-select');
    if (slotSelect) {
      slotSelect.value = selectedSlot;
    }
    renderReportTable();
  }

  return {
    init,
    setReportType,
    onSlotSelectChange,
    applySlotFilter,
    exportPDF,
    exportExcel
  };
})();

window.ReportsModule = ReportsModule;
