// Video inspector & model tester

const InspectorModule = (() => {
  let selectedFile = null;
  let isAnalyzing = false;

  async function loadModels() {
    const select = document.getElementById('inspect-model-select');
    if (!select) return;

    try {
      const res = await fetch('/api/models');
      if (!res.ok) return;
      const data = await res.json();
      const models = data.models || [];

      select.innerHTML = models.map(m => `
        <option value="${m.name}" ${m.name === data.default ? 'selected' : ''}>
          ${m.name} (${m.size_mb} MB) — ${m.description}
        </option>
      `).join('');
    } catch (e) {
      console.warn('Could not load models list:', e);
    }
  }

  function handleFileSelected(file) {
    if (!file) return;
    selectedFile = file;

    const fileLabel = document.getElementById('selected-file-label');
    const dropzoneContent = document.getElementById('dropzone-default-content');
    const dropzoneSelected = document.getElementById('dropzone-selected-content');

    if (fileLabel) {
      const sizeMb = (file.size / (1024 * 1024)).toFixed(1);
      fileLabel.textContent = `${file.name} (${sizeMb} MB)`;
    }
    if (dropzoneContent) dropzoneContent.style.display = 'none';
    if (dropzoneSelected) dropzoneSelected.style.display = 'block';
  }

  function clearSelectedFile() {
    selectedFile = null;
    const fileInput = document.getElementById('video-file-input');
    if (fileInput) fileInput.value = '';

    const dropzoneContent = document.getElementById('dropzone-default-content');
    const dropzoneSelected = document.getElementById('dropzone-selected-content');
    if (dropzoneContent) dropzoneContent.style.display = 'block';
    if (dropzoneSelected) dropzoneSelected.style.display = 'none';
  }

  function useSampleVideo(sampleName = 'traffic.mp4') {
    selectedFile = null;
    const fileLabel = document.getElementById('selected-file-label');
    const dropzoneContent = document.getElementById('dropzone-default-content');
    const dropzoneSelected = document.getElementById('dropzone-selected-content');

    if (fileLabel) {
      fileLabel.textContent = `Plaza Video: ${sampleName} (Local Storage)`;
    }
    if (dropzoneContent) dropzoneContent.style.display = 'none';
    if (dropzoneSelected) dropzoneSelected.style.display = 'block';
  }

  async function startVideoInspection() {
    if (isAnalyzing) return;

    const modelSelect = document.getElementById('inspect-model-select');
    const confInput = document.getElementById('inspect-conf-input');
    const ocrCheck = document.getElementById('inspect-ocr-toggle');
    const frameStepSelect = document.getElementById('inspect-step-select');
    const maxFramesInput = document.getElementById('inspect-frames-input');

    const model = modelSelect ? modelSelect.value : 'best.pt';
    const conf = confInput ? confInput.value : '0.20';
    const enableOcr = ocrCheck ? ocrCheck.checked : true;
    const frameStep = frameStepSelect ? frameStepSelect.value : '2';
    const maxFrames = maxFramesInput ? maxFramesInput.value : '300';

    const formData = new FormData();
    formData.append('model', model);
    formData.append('confidence', conf);
    formData.append('enable_ocr', enableOcr);
    formData.append('frame_step', frameStep);
    formData.append('max_frames', maxFrames);

    if (selectedFile) {
      formData.append('video', selectedFile);
    } else {
      formData.append('sample_video', 'traffic.mp4');
    }

    const btn = document.getElementById('btn-run-inspection');
    const statusBox = document.getElementById('inspector-status-box');
    const statusText = document.getElementById('inspector-status-text');
    const resultsContainer = document.getElementById('inspector-results-container');

    isAnalyzing = true;
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span>Processing Video with AI...`;
    }
    if (statusBox) statusBox.style.display = 'block';
    if (statusText) statusText.textContent = `Analyzing frames with ${model} & ANPR... Please wait...`;
    if (resultsContainer) resultsContainer.style.opacity = '0.4';

    const startTime = Date.now();
    const timerInterval = setInterval(() => {
      const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
      if (statusText && isAnalyzing) {
        statusText.textContent = `Processing frames with ${model}... (${elapsed}s elapsed)`;
      }
    }, 500);

    try {
      const res = await fetch('/api/model/inspect-video', {
        method: 'POST',
        body: formData
      });

      clearInterval(timerInterval);
      const data = await res.json();

      if (!res.ok || !data.success) {
        throw new Error(data.error || 'Video analysis failed');
      }

      renderInspectionResults(data);
      if (typeof App !== 'undefined' && App.toast) {
        App.toast(`Analysis complete: ${data.stats.total_vehicles} vehicles detected!`, 'success');
      }
    } catch (err) {
      console.error('Inspection error:', err);
      if (typeof App !== 'undefined' && App.toast) {
        App.toast(`Inspection failed: ${err.message}`, 'error');
      }
      if (statusText) statusText.textContent = `Error: ${err.message}`;
    } finally {
      clearInterval(timerInterval);
      isAnalyzing = false;
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = `<i class="bi bi-play-circle-fill me-2"></i>Run AI Model Analysis`;
      }
      if (statusBox) statusBox.style.display = 'none';
      if (resultsContainer) resultsContainer.style.opacity = '1';
    }
  }

  function renderInspectionResults(data) {
    const container = document.getElementById('inspector-results-container');
    if (!container) return;

    container.style.display = 'block';

    const stats = data.stats || {};
    const detections = data.detections || [];
    const videoUrl = data.video_url;

    // 1. Update Video Player & Download Action Links
    const player = document.getElementById('inspector-video-player');
    const videoSource = document.getElementById('inspector-video-source');
    const downloadBtn = document.getElementById('inspector-video-download-btn');
    const newtabBtn = document.getElementById('inspector-video-newtab-btn');
    const directLink = document.getElementById('inspector-video-direct-link');

    if (videoUrl) {
      const fullVideoUrl = videoUrl + '?t=' + Date.now();
      if (player) {
        // Setting src directly on <video> element is required for Chrome/Safari dynamic updates
        player.src = fullVideoUrl;
        if (videoSource) videoSource.src = fullVideoUrl;
        player.load();
        player.play().catch(() => {});
        
        player.onerror = () => {
          showToast('Video ready! If in-browser preview doesn\'t play due to codec, click "Download MP4" to watch in QuickTime / VLC.', 'info');
        };
      }

      if (downloadBtn) {
        downloadBtn.href = videoUrl;
        downloadBtn.style.display = 'inline-flex';
      }
      if (newtabBtn) {
        newtabBtn.href = videoUrl;
        newtabBtn.style.display = 'inline-flex';
      }
      if (directLink) {
        directLink.href = videoUrl;
        directLink.style.display = 'inline-block';
      }
    }

    // 2. Update KPI Stats
    const elVehicles = document.getElementById('kpi-inspect-vehicles');
    const elToll = document.getElementById('kpi-inspect-toll');
    const elFps = document.getElementById('kpi-inspect-fps');
    const elModel = document.getElementById('kpi-inspect-model');

    const totalPlatesRead = (detections || []).filter(d => d.plate_number && !d.plate_number.startsWith('UNREGISTERED')).length;

    if (elVehicles) elVehicles.textContent = (stats.total_vehicles || 0).toLocaleString();
    if (elToll) elToll.textContent = `${totalPlatesRead} Plates`;
    if (elFps) elFps.textContent = `${stats.fps || 0} FPS (${stats.processing_time_sec || 0}s)`;
    if (elModel) elModel.textContent = stats.model_used || 'YOLOv8';

    // 3. Render Breakdown Chips
    const breakdownContainer = document.getElementById('inspector-breakdown-chips');
    if (breakdownContainer && stats.by_type) {
      const chips = Object.entries(stats.by_type).map(([type, count]) => {
        return `
          <div class="inspector-badge-chip">
            <span style="font-weight:700; color:#60a5fa;">${type}:</span>
            <span>${count}</span>
          </div>
        `;
      }).join('');
      breakdownContainer.innerHTML = chips || '<span style="color:#94a3b8; font-size:12px;">No vehicles detected</span>';
    }

    // 4. Render Detections Table
    const tbody = document.getElementById('inspector-detections-tbody');
    if (tbody) {
      if (detections.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" class="text-center py-4" style="color:#94a3b8;">No vehicle records detected in the sample range</td></tr>`;
      } else {
        tbody.innerHTML = detections.map((d, idx) => {
          const isPlateValid = d.plate_number && !d.plate_number.startsWith('UNREGISTERED');
          const plateBadgeClass = isPlateValid ? 'bd-plate-badge' : 'bd-plate-badge plate-unregistered';
          const cropImg = d.crop_url ? `<img src="${d.crop_url}" class="crop-thumbnail-card" title="Click to view full vehicle" onclick="window.open('${d.crop_url}','_blank')">` : `<span style="color:#64748b; font-size:11px;">N/A</span>`;

          return `
            <tr>
              <td style="font-size:12px; font-weight:600; color:#94a3b8;">#${idx + 1}</td>
              <td style="font-size:12px; font-family:monospace; color:#38bdf8;">
                <a href="javascript:void(0)" onclick="InspectorModule.seekVideo(${d.timestamp_sec})" title="Jump to frame" style="color:#38bdf8; text-decoration:none;">
                  <i class="bi bi-play-circle me-1"></i>${d.time_str}
                </a>
              </td>
              <td>${cropImg}</td>
              <td>
                <span class="badge" style="background:rgba(59,130,246,0.15); color:#60a5fa; border:1px solid rgba(59,130,246,0.3); font-weight:600;">
                  ${d.vehicle_type}
                </span>
              </td>
              <td>
                <span class="badge" style="background:rgba(16,185,129,0.15); color:#34d399; font-size:11px; border:1px solid rgba(16,185,129,0.3);">
                  <i class="bi bi-check2 me-1"></i>Verified
                </span>
              </td>
              <td>
                <span class="${plateBadgeClass}">
                  <i class="bi bi-card-text"></i> ${d.plate_number}
                </span>
                ${d.plate_confidence > 0 ? `<small style="color:#34d399; font-size:10px; margin-left:4px;">${d.plate_confidence.toFixed(0)}% OCR</small>` : ''}
              </td>
              <td>
                <div class="d-flex align-items-center gap-2">
                  <div class="progress" style="width:50px; height:6px; background:rgba(255,255,255,0.08);">
                    <div class="progress-bar bg-primary" style="width:${d.confidence}%"></div>
                  </div>
                  <small style="color:#cbd5e1; font-size:11px;">${d.confidence}%</small>
                </div>
              </td>
            </tr>
          `;
        }).join('');
      }
    }
  }

  function seekVideo(timeSec) {
    const player = document.getElementById('inspector-video-player');
    if (player && !isNaN(timeSec)) {
      player.currentTime = Math.max(0, timeSec - 0.5);
      player.play().catch(() => {});
    }
  }

  async function testDirectPlateOCR(file) {
    if (!file) return;
    const resultBox = document.getElementById('plate-ocr-result-box');
    const resultText = document.getElementById('plate-ocr-result-text');
    const resultRaw = document.getElementById('plate-ocr-result-raw');
    const resultConf = document.getElementById('plate-ocr-result-conf');
    const previewImg = document.getElementById('plate-ocr-preview-img');

    if (resultBox) resultBox.style.display = 'block';
    if (resultText) resultText.textContent = 'Analyzing plate image with ANPR...';
    if (resultConf) resultConf.textContent = 'Processing...';
    if (resultRaw) resultRaw.textContent = '';

    // Show instant image preview
    if (previewImg) {
      try {
        previewImg.src = URL.createObjectURL(file);
        previewImg.style.display = 'block';
      } catch (err) {}
    }

    const formData = new FormData();
    formData.append('image', file);

    try {
      const res = await fetch('/api/ocr/test-plate', {
        method: 'POST',
        body: formData
      });

      const contentType = res.headers.get('content-type') || '';
      let data = {};
      if (contentType.includes('application/json')) {
        data = await res.json();
      } else {
        const text = await res.text();
        throw new Error(`Server returned non-JSON response (${res.status}). Check server console.`);
      }

      if (res.ok && data.success) {
        if (resultText) resultText.textContent = data.plate_number || 'Detected';
        if (resultConf) {
          resultConf.className = 'badge bg-success-subtle text-success border border-success-subtle';
          resultConf.textContent = `${(data.confidence || 90).toFixed(1)}% Confidence`;
        }
        if (resultRaw) resultRaw.textContent = `Raw OCR Output: ${data.raw_text || 'None'}`;
      } else {
        if (resultText) resultText.textContent = data.plate_number || 'No plate detected';
        if (resultConf) {
          resultConf.className = 'badge bg-warning-subtle text-warning border border-warning-subtle';
          resultConf.textContent = 'Uncertain';
        }
        if (resultRaw) resultRaw.textContent = data.error || 'Please upload a clear crop of the license plate with readable characters.';
      }
    } catch (e) {
      if (resultText) resultText.textContent = 'Recognition Error';
      if (resultConf) {
        resultConf.className = 'badge bg-danger-subtle text-danger border border-danger-subtle';
        resultConf.textContent = 'Failed';
      }
      if (resultRaw) resultRaw.textContent = e.message;
    }
  }

  function init() {
    loadModels();

    // Dropzone listeners
    const dropzone = document.getElementById('video-dropzone');
    const fileInput = document.getElementById('video-file-input');

    if (dropzone && fileInput) {
      dropzone.addEventListener('click', (e) => {
        if (!e.target.closest('#btn-clear-selected-video')) {
          fileInput.click();
        }
      });

      fileInput.addEventListener('change', (e) => {
        if (e.target.files && e.target.files[0]) {
          handleFileSelected(e.target.files[0]);
        }
      });

      dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropzone.classList.add('dragover');
      });

      dropzone.addEventListener('dragleave', () => {
        dropzone.classList.remove('dragover');
      });

      dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.classList.remove('dragover');
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
          handleFileSelected(e.dataTransfer.files[0]);
        }
      });
    }

    // Plate test file input
    const plateInput = document.getElementById('plate-test-input');
    if (plateInput) {
      plateInput.addEventListener('change', (e) => {
        if (e.target.files && e.target.files[0]) {
          testDirectPlateOCR(e.target.files[0]);
        }
      });
    }
  }

  return {
    init,
    startVideoInspection,
    clearSelectedFile,
    useSampleVideo,
    seekVideo,
    testDirectPlateOCR
  };
})();

window.InspectorModule = InspectorModule;

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  InspectorModule.init();
});

