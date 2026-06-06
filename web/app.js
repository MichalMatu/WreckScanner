// ─── PIPELINE (klein i analiza w jednym) ────────
const btnRun = document.getElementById('btn-run');
const spinner = document.getElementById('spinner');
const runIcon = document.getElementById('run-icon');
const statusEl = document.getElementById('status');
const progressEl = document.getElementById('progress');
const btnReport = document.getElementById('btn-report');
const reportLabelEl = document.getElementById('report-label');
const resultActions = document.getElementById('result-actions');

let candidateMarkers = [];
let imageOverlay = null;
let scanArea = null;

function clearCandidateMarkers() {
    candidateMarkers.forEach(m => map.removeLayer(m));
    candidateMarkers = [];
}

function clearResults() {
    clearCandidateMarkers();
    currentJobToken = null;
    if (imageOverlay) {
        map.removeLayer(imageOverlay);
        imageOverlay = null;
    }
    if (scanArea) {
        map.removeLayer(scanArea);
        scanArea = null;
    }
    statusEl.textContent = '';
    statusEl.className = '';
    resetProgress();
}

function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, ch => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;',
    }[ch]));
}
