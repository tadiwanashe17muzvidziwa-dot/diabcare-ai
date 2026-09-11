const DEFAULT_REMOTE_API = 'https://your-app.onrender.com/api';
const _savedApi = localStorage.getItem('diabcare_api_url');
const _isCapacitor = !!(window.Capacitor && window.Capacitor.isNativePlatform && window.Capacitor.isNativePlatform());
const _isFileProto = location.protocol === 'file:' || location.protocol === 'capacitor:';
const API_BASE = (_savedApi || ((_isCapacitor || _isFileProto) ? DEFAULT_REMOTE_API : '/api')).replace(/\/$/, '');
const API_KEY = localStorage.getItem('diabcare_api_key') || '';
// Per-phone ID: each phone/browser gets its own random ID once,
// so /api/stats + history only show YOUR scans.
let DEVICE_ID = localStorage.getItem('diabcare_device_id') || '';
if (!DEVICE_ID) {
    DEVICE_ID = 'dev-' + Math.random().toString(36).slice(2, 10) + Date.now().toString(36);
    localStorage.setItem('diabcare_device_id', DEVICE_ID);
}
function apiHeaders(extra = {}) {
    const h = { 'X-Device-Id': DEVICE_ID, ...extra };
    if (API_KEY) h['X-API-Key'] = API_KEY;
    return h;
}
function resolveApiUrl(u) {
    if (!u) return u;
    if (u.startsWith('http')) return u;
    // server returns relative /api/image/... -> prefix with API origin when remote
    if (u.startsWith('/api/') && API_BASE.startsWith('http')) {
        const origin = API_BASE.replace(/\/api$/, '');
        return origin + u;
    }
    return u;
}
function openSettings() {
    const url = prompt('Backend API URL (e.g. https://your-app.onrender.com/api):', localStorage.getItem('diabcare_api_url') || API_BASE);
    if (url === null) return;
    const key = prompt('API Key (X-API-Key, leave empty if none):', localStorage.getItem('diabcare_api_key') || '');
    if (key === null) return;
    if (url.trim()) localStorage.setItem('diabcare_api_url', url.trim().replace(/\/$/, ''));
    else localStorage.removeItem('diabcare_api_url');
    if (key.trim()) localStorage.setItem('diabcare_api_key', key.trim());
    else localStorage.removeItem('diabcare_api_key');
    location.reload();
}
let currentScanId = null;
let allScans = [];

document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initUpload();
    loadDashboard();
});

function initNavigation() {
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const section = item.dataset.section;
            showSection(section);
        });
    });
}

function showSection(sectionId) {
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));

    document.getElementById(sectionId).classList.add('active');
    document.querySelector(`[data-section="${sectionId}"]`).classList.add('active');

    if (sectionId === 'dashboard') loadDashboard();
    if (sectionId === 'history') loadHistory();
}

function initUpload() {
    const uploadArea = document.getElementById('upload-area');
    const fileInput = document.getElementById('file-input');

    uploadArea.addEventListener('click', () => fileInput.click());

    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });

    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragover');
    });

    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        const files = e.dataTransfer.files;
        if (files.length > 0) handleFile(files[0]);
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) handleFile(e.target.files[0]);
    });
}

function handleFile(file) {
    if (!file.type.startsWith('image/')) {
        showToast('Please upload an image file', 'error');
        return;
    }
    if (file.size > 8 * 1024 * 1024) {
        showToast('Image too large (max 8MB)', 'error');
        return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
        document.getElementById('preview-img').src = e.target.result;
        document.getElementById('upload-area').style.display = 'none';
        document.getElementById('preview-area').style.display = 'block';
        document.getElementById('result-area').style.display = 'none';
    };
    reader.readAsDataURL(file);
}

function resetUpload() {
    document.getElementById('upload-area').style.display = 'block';
    document.getElementById('preview-area').style.display = 'none';
    document.getElementById('result-area').style.display = 'none';
    document.getElementById('file-input').value = '';
    document.getElementById('preview-img').src = '';
}

async function analyzeImage() {
    const fileInput = document.getElementById('file-input');
    const file = fileInput.files[0];

    if (!file) {
        showToast('No image selected', 'error');
        return;
    }

    showLoading(true);

    const formData = new FormData();
    formData.append('image', file);

    try {
        const response = await fetch(`${API_BASE}/analyze`, {
            method: 'POST',
            headers: apiHeaders(),
            body: formData
        });

        const text = await response.text();
        let result;
        try {
            result = JSON.parse(text);
        } catch (e) {
            throw new Error('Server returned an invalid response (HTTP ' + response.status + ')');
        }

        if (response.ok) {
            displayResult(result);
            currentScanId = result.scan_id;
            showToast('Analysis complete!', 'success');
        } else {
            showToast(result.error || 'Analysis failed', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showToast(error.message || 'Connection error. Please try again.', 'error');
    } finally {
        showLoading(false);
    }
}

function displayResult(result) {
    document.getElementById('preview-area').style.display = 'none';
    document.getElementById('result-area').style.display = 'block';

    document.getElementById('result-img').src =
        `${API_BASE}/image/${encodeURIComponent(result.filename)}`;
    if (result.heatmap_url) {
        document.getElementById('heatmap-img').src = resolveApiUrl(result.heatmap_url);
        document.getElementById('heatmap-img').style.display = 'block';
    } else {
        document.getElementById('heatmap-img').style.display = 'none';
    }

    const predictionBadge = document.getElementById('prediction-badge');
    const predictionText = document.getElementById('prediction-text');
    predictionText.textContent = result.prediction.toUpperCase();
    predictionBadge.className = 'prediction-badge ' + result.prediction.toLowerCase();

    const confidenceBar = document.getElementById('confidence-bar');
    const confidenceText = document.getElementById('confidence-text');
    confidenceBar.style.width = result.confidence + '%';
    confidenceText.textContent = result.confidence + '%';

    const riskBadge = document.getElementById('risk-badge');
    const riskText = document.getElementById('risk-text');
    riskText.textContent = result.risk_level + ' RISK';
    riskBadge.className = 'risk-badge ' + result.risk_level.toLowerCase();

    const recommendationsList = document.getElementById('recommendations-list');
    recommendationsList.innerHTML = '';
    result.recommendations.forEach(rec => {
        const li = document.createElement('li');
        li.textContent = rec;
        recommendationsList.appendChild(li);
    });
}

async function downloadReport() {
    if (!currentScanId) {
        showToast('No scan to generate report for', 'error');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/report/${currentScanId}`, {
            headers: apiHeaders()
        });
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `DiabCare_Report_${currentScanId}.pdf`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            showToast('Report downloaded!', 'success');
        } else {
            showToast('Failed to generate report', 'error');
        }
    } catch (error) {
        showToast('Error generating report', 'error');
    }
}

async function loadDashboard() {
    try {
        const response = await fetch(`${API_BASE}/stats`, { headers: apiHeaders() });
        const stats = await response.json();

        document.getElementById('total-scans').textContent = stats.total_scans;
        document.getElementById('low-risk').textContent = stats.low_risk;
        document.getElementById('medium-risk').textContent = stats.medium_risk;
        document.getElementById('high-risk').textContent = stats.high_risk;

        const historyResponse = await fetch(`${API_BASE}/history`, { headers: apiHeaders() });
        allScans = await historyResponse.json();
        renderRecentScans(allScans.slice(0, 5));
    } catch (error) {
        console.error('Error loading dashboard:', error);
    }
}

function renderRecentScans(scans) {
    const container = document.getElementById('recent-scans-list');

    if (scans.length === 0) {
        container.innerHTML = '<p class="empty-state">No scans yet. Start your first scan!</p>';
        return;
    }

    container.innerHTML = scans.map(scan => `
        <div class="scan-item">
            <div class="scan-item-icon ${scan.risk_level.toLowerCase()}">
                <i class="fas fa-${scan.risk_level === 'HIGH' ? 'exclamation-triangle' : scan.risk_level === 'MEDIUM' ? 'exclamation-circle' : 'check-circle'}"></i>
            </div>
            <div class="scan-item-info">
                <h4>${scan.prediction} - ${scan.risk_level}</h4>
                <p>${new Date(scan.created_at).toLocaleDateString()}</p>
            </div>
        </div>
    `).join('');
}

async function loadHistory() {
    try {
        const response = await fetch(`${API_BASE}/history`, { headers: apiHeaders() });
        allScans = await response.json();
        renderHistory(allScans);
    } catch (error) {
        showToast('Error loading history', 'error');
    }
}

function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, c => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[c]));
}

function renderHistory(scans) {
    const container = document.getElementById('history-grid');

    if (scans.length === 0) {
        container.innerHTML = '<p class="empty-state">No scan history available.</p>';
        return;
    }

    container.innerHTML = scans.map(scan => `
        <div class="history-card" data-risk="${escapeHtml(scan.risk_level)}">
            <div class="history-card-image">
                <img src="${API_BASE}/image/${encodeURIComponent(scan.filename)}" alt="Scan" loading="lazy">
            </div>
            <div class="history-card-content">
                <div class="history-card-header">
                    <h4>Scan #${scan.id}</h4>
                    <span class="history-card-date">${new Date(scan.created_at).toLocaleDateString()}</span>
                </div>
                <div class="history-card-meta">
                    <span class="meta-badge ${escapeHtml(scan.prediction.toLowerCase())}">${escapeHtml(scan.prediction)}</span>
                    <span class="meta-badge ${escapeHtml(scan.risk_level.toLowerCase())}">${escapeHtml(scan.risk_level)}</span>
                </div>
                <div class="history-card-actions">
                    <button class="btn btn-secondary" onclick="viewScan(${scan.id})">
                        <i class="fas fa-eye"></i> View
                    </button>
                    <button class="btn btn-secondary" onclick="downloadReportById(${scan.id})">
                        <i class="fas fa-file-pdf"></i> Report
                    </button>
                    <button class="btn btn-secondary" onclick="deleteScan(${scan.id})">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        </div>
    `).join('');
}

function filterHistory() {
    const searchTerm = document.getElementById('history-search').value.toLowerCase();
    const filtered = allScans.filter(scan =>
        scan.filename.toLowerCase().includes(searchTerm) ||
        scan.prediction.toLowerCase().includes(searchTerm) ||
        scan.risk_level.toLowerCase().includes(searchTerm)
    );
    renderHistory(filtered);
}

function filterByRisk(risk) {
    document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelector(`[data-filter="${risk}"]`).classList.add('active');

    if (risk === 'all') {
        renderHistory(allScans);
    } else {
        const filtered = allScans.filter(scan => scan.risk_level === risk);
        renderHistory(filtered);
    }
}

function viewScan(scanId) {
    showSection('scan');
    loadScanById(scanId);
}

async function loadScanById(scanId) {
    try {
        const response = await fetch(`${API_BASE}/scan/${scanId}`, { headers: apiHeaders() });
        const scan = await response.json();

        currentScanId = scan.id;
        // heatmap_path is a server path like .../heatmap_<uuid>.jpg -> extract basename
        let heatmap_url = null;
        if (scan.heatmap_path) {
            const base = scan.heatmap_path.split(/[/\\]/).pop();
            if (base) heatmap_url = `${API_BASE}/image/${encodeURIComponent(base)}`;
        }
        displayResult({ ...scan, heatmap_url });
    } catch (error) {
        showToast('Error loading scan', 'error');
    }
}

async function downloadReportById(scanId) {
    currentScanId = scanId;
    await downloadReport();
}

async function deleteScan(scanId) {
    if (!confirm('Are you sure you want to delete this scan?')) return;

    try {
        const response = await fetch(`${API_BASE}/scan/${scanId}`, {
            method: 'DELETE',
            headers: apiHeaders()
        });

        if (response.ok) {
            showToast('Scan deleted', 'success');
            loadHistory();
        } else {
            showToast('Error deleting scan', 'error');
        }
    } catch (error) {
        showToast('Error deleting scan', 'error');
    }
}

function showLoading(show) {
    document.getElementById('loading-overlay').style.display = show ? 'flex' : 'none';
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    const icons = {
        success: 'fa-check-circle',
        error: 'fa-exclamation-circle',
        info: 'fa-info-circle'
    };

    toast.innerHTML = `
        <i class="fas ${icons[type]}"></i>
        <span>${message}</span>
    `;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideIn 0.3s ease reverse';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}
