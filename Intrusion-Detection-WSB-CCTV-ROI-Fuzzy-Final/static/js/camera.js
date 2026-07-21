const startButton = document.getElementById('startButton');
const stopButton = document.getElementById('stopButton');
const cameraFeed = document.getElementById('cameraFeed');
const statusBox = document.getElementById('status');
const detectionCount = document.getElementById('detectionCount');
const finalStatus = document.getElementById('finalStatus');
const riskScore = document.getElementById('riskScore');
const detectionList = document.getElementById('detectionList');
const flipCamera = document.getElementById('flipCamera');
const roiDetectionCount = document.getElementById('roiDetectionCount');
const insideRoiCount = document.getElementById('insideRoiCount');
const fuzzyClass = document.getElementById('fuzzyClass');
const fuzzyScore = document.getElementById('fuzzyScore');
let pollTimer = null;

function setStatus(text, statusName = '') {
  statusBox.textContent = text;
  statusBox.className = `status ${statusName}`.trim();
}

async function startCamera() {
  startButton.disabled = true;
  setStatus('Starting camera…');
  try {
    const response = await fetch('/start-camera', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({flip_camera: flipCamera.checked})
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.message || 'Could not start camera.');
    cameraFeed.src = `/video-feed?ts=${Date.now()}`;
    stopButton.disabled = false;
    setStatus('Camera running', 'non_intrusion');
    pollTimer = window.setInterval(loadDetections, 800);
  } catch (error) {
    startButton.disabled = false;
    setStatus(error.message);
  }
}

async function stopCamera() {
  stopButton.disabled = true;
  if (pollTimer) window.clearInterval(pollTimer);
  pollTimer = null;
  await fetch('/stop-camera', {method: 'POST'});
  cameraFeed.removeAttribute('src');
  startButton.disabled = false;
  detectionCount.textContent = '0';
  finalStatus.textContent = '—';
  riskScore.textContent = '0';
  if (roiDetectionCount) roiDetectionCount.textContent = '0';
  if (insideRoiCount) insideRoiCount.textContent = '0';
  if (fuzzyClass) fuzzyClass.textContent = '—';
  if (fuzzyScore) fuzzyScore.textContent = '0';
  detectionList.innerHTML = '<p class="muted">No detections yet.</p>';
  setStatus('Camera stopped');
}

async function loadDetections() {
  try {
    const response = await fetch('/get-detections', {cache: 'no-store'});
    const data = await response.json();
    const decision = data.decision || {};
    const fuzzy = decision.fuzzy_result || {};
    detectionCount.textContent = data.count ?? 0;
    finalStatus.textContent = (decision.status || data.status || 'unknown').replaceAll('_', ' ');
    riskScore.textContent = Number(decision.risk_score || 0).toFixed(1);
    const roiSummary = data.roi_summary || {};
    if (roiDetectionCount) roiDetectionCount.textContent = roiSummary.roi_model_detection_count ?? 0;
    if (insideRoiCount) insideRoiCount.textContent = roiSummary.inside_roi_count ?? 0;
    if (fuzzyClass) fuzzyClass.textContent = fuzzy.fuzzy_class || '—';
    if (fuzzyScore) fuzzyScore.textContent = Number(fuzzy.fuzzy_score || 0).toFixed(1);
    setStatus(
      decision.status === 'intrusion' ? 'ROI intrusion alert confirmed' : 'No ROI intrusion alert',
      decision.status === 'intrusion' ? 'intrusion' : 'non_intrusion'
    );

    const detections = data.detections || [];
    if (!detections.length) {
      detectionList.innerHTML = '<p class="muted">No intrusion candidates in the current frame.</p>';
      return;
    }
    detectionList.innerHTML = detections.map(item => `
      <div class="detection">
        <b>${item.model_class || 'intrusion'}</b><br>
        Confidence: ${(Number(item.confidence || 0) * 100).toFixed(1)}%<br>
        Risk: ${Number(item.risk_score || 0).toFixed(1)} · Track: ${item.track_id ?? '—'}<br>
        ROI: ${item.roi_status || 'not checked'} · Context: ${item.roi_context_class || '—'}<br>
        Fuzzy: ${item.fuzzy_class || fuzzy.fuzzy_class || '—'} · Score: ${Number(item.fuzzy_score || fuzzy.fuzzy_score || 0).toFixed(1)}
      </div>`).join('');
  } catch (error) {
    console.error(error);
  }
}

startButton.addEventListener('click', startCamera);
stopButton.addEventListener('click', stopCamera);
window.addEventListener('beforeunload', () => {
  if (!stopButton.disabled) navigator.sendBeacon('/stop-camera');
});
