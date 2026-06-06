let geotiffCacheLayer = null;
let geotiffCacheRectanglesByFile = new Map();
let selectedGeotiffCacheFile = null;

function geotiffSizeLabel(bytes) {
    const value = Number(bytes || 0);
    if (value >= 1024 * 1024 * 1024) return `${(value / (1024 * 1024 * 1024)).toFixed(2)} GB`;
    if (value >= 1024 * 1024) return `${(value / (1024 * 1024)).toFixed(1)} MB`;
    return `${Math.ceil(value / 1024)} KB`;
}

function geotiffCacheFileName(value) {
    const file = String(value ?? '').trim();
    if (!file || file.includes('/') || file.includes('\\')) return '';
    return file;
}

function geotiffCacheStatusClass(status) {
    return String(status || 'unknown').replace(/[^A-Za-z0-9_-]/g, '') || 'unknown';
}

function geotiffCacheRectangleStyle(selected = false) {
    return selected
        ? {
            color: '#fbbf24',
            weight: 4,
            fillColor: '#f59e0b',
            fillOpacity: 0.18,
            interactive: true,
        }
        : {
            color: '#16a34a',
            weight: 2,
            fillColor: '#22c55e',
            fillOpacity: 0.08,
            interactive: true,
        };
}

function clearGeotiffCacheLayer(options = {}) {
    if (geotiffCacheLayer) {
        map.removeLayer(geotiffCacheLayer);
        geotiffCacheLayer = null;
    }
    geotiffCacheRectanglesByFile.clear();
    if (options?.resetSelection !== false) {
        selectedGeotiffCacheFile = null;
        updateGeotiffCacheSelection();
    }
}

function updateGeotiffCacheSelection(options = {}) {
    const selectedFile = geotiffCacheFileName(selectedGeotiffCacheFile);
    let selectedRow = null;
    document.querySelectorAll('#geotiff-cache-list .geotiff-cache-item').forEach(row => {
        const active = Boolean(selectedFile) && geotiffCacheFileName(row.dataset.file) === selectedFile;
        row.classList.toggle('is-selected', active);
        row.setAttribute('aria-selected', active ? 'true' : 'false');
        if (active) selectedRow = row;
    });

    geotiffCacheRectanglesByFile.forEach((rect, file) => {
        rect.setStyle(geotiffCacheRectangleStyle(file === selectedFile));
    });

    const rect = selectedFile ? geotiffCacheRectanglesByFile.get(selectedFile) : null;
    if (!rect) return;
    rect.bringToFront();
    if (options.scrollList && selectedRow) {
        selectedRow.scrollIntoView({ block: 'nearest' });
    }
    if (options.pan) {
        map.fitBounds(rect.getBounds().pad(0.05), { padding: [36, 36], maxZoom: 16 });
    }
    if (options.openPopup) {
        rect.openPopup();
    }
}

function selectGeotiffCacheItem(fileName, options = {}) {
    const file = geotiffCacheFileName(fileName);
    if (!file) return;
    selectedGeotiffCacheFile = file;
    updateGeotiffCacheSelection(options);
}

function renderGeotiffCacheLayer(data = {}) {
    clearGeotiffCacheLayer({ resetSelection: false });
    const rectangles = (Array.isArray(data.coverage) ? data.coverage : [])
        .map(item => {
            const file = geotiffCacheFileName(item.file);
            const bounds = item.bounds_4326 || {};
            const minLat = Number(bounds.min_lat);
            const minLon = Number(bounds.min_lon);
            const maxLat = Number(bounds.max_lat);
            const maxLon = Number(bounds.max_lon);
            if (![minLat, minLon, maxLat, maxLon].every(Number.isFinite)) return null;
            const rect = L.rectangle(
                [[minLat, minLon], [maxLat, maxLon]],
                geotiffCacheRectangleStyle(file === selectedGeotiffCacheFile)
            );
            rect.bindPopup(`
                <div class="map-popup">
                    <b>${escapeHtml(item.file || 'GeoTIFF')}</b><br>
                    ${escapeHtml(geotiffSizeLabel(item.size_bytes))}
                </div>
            `);
            if (file) {
                geotiffCacheRectanglesByFile.set(file, rect);
                rect.on('click', () => selectGeotiffCacheItem(file, { scrollList: true }));
            }
            return rect;
        })
        .filter(Boolean);
    if (!rectangles.length) {
        updateGeotiffCacheSelection();
        return;
    }
    geotiffCacheLayer = L.layerGroup(rectangles).addTo(map);
    updateGeotiffCacheSelection();
}

function renderGeotiffCacheStatus(data = {}) {
    const status = document.getElementById('geotiff-cache-status');
    const list = document.getElementById('geotiff-cache-list');
    const summary = data.summary || {};
    const estimate = data.estimate || {};
    if (status) {
        status.textContent = t('modal.geotiffCache.status', {
            total: geotiffSizeLabel(summary.total_bytes),
            files: summary.completed_files || 0,
            partials: summary.partial_files || 0,
            estimate: estimate.total_gb != null ? `${estimate.total_gb} GB` : '-',
        });
    }
    if (!list) return;
    const items = Array.isArray(data.items) ? data.items : [];
    const availableFiles = new Set(items.map(item => geotiffCacheFileName(item.file)).filter(Boolean));
    if (selectedGeotiffCacheFile && !availableFiles.has(selectedGeotiffCacheFile)) {
        selectedGeotiffCacheFile = null;
    }
    list.innerHTML = items.slice(0, 80).map(item => `
        <div class="geotiff-cache-item geotiff-cache-item--${geotiffCacheStatusClass(item.status)}" role="button"
            tabindex="0" aria-selected="false" data-file="${escapeHtml(geotiffCacheFileName(item.file))}">
            <strong>${escapeHtml(item.file || '-')}</strong>
            <span>${escapeHtml(item.status || '-')} · ${escapeHtml(geotiffSizeLabel(item.size_bytes))}</span>
            <button type="button" class="geotiff-cache-delete" data-file="${escapeHtml(geotiffCacheFileName(item.file))}"
                title="${escapeHtml(t('modal.geotiffCache.delete'))}"
                aria-label="${escapeHtml(`${t('modal.geotiffCache.delete')}: ${item.file || '-'}`)}">
                <svg viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M9 3h6l1 2h5v2h-2l-1 14H6L5 7H3V5h5l1-2zm-1 4 .86 12h6.28L16 7H8zm2 2h2v8h-2V9zm4 0h2v8h-2V9z" />
                </svg>
            </button>
        </div>
    `).join('') || `<p class="modal-hint">${escapeHtml(t('modal.geotiffCache.empty'))}</p>`;
    renderGeotiffCacheLayer(data);
}

async function loadGeotiffCacheStatus() {
    if (!adminAuthenticated && !(await ensureAdmin())) return;
    const status = document.getElementById('geotiff-cache-status');
    if (status) status.textContent = t('modal.geotiffCache.loading');
    try {
        const data = await apiJson(`${ADMIN_GEOTIFF_CACHE_URL}?ts=${Date.now()}`, { cache: 'no-store' });
        if (data.status !== 'ok') {
            throw new Error(data.error || t('modal.geotiffCache.loadError'));
        }
        renderGeotiffCacheStatus(data);
    } catch (err) {
        if (status) status.textContent = apiErrorMessage(err, t('modal.geotiffCache.loadError'));
    }
}

async function openGeotiffCacheModal() {
    if (!(await ensureAdmin())) return;
    openModal('modal-geotiff-cache');
    await loadGeotiffCacheStatus();
}

async function deleteGeotiffCacheItem(fileName, button = null) {
    if (!(await ensureAdmin())) return;
    const file = geotiffCacheFileName(fileName);
    if (!file) return;
    const confirmed = await confirmAction({
        title: t('modal.geotiffCache.deleteTitle'),
        message: t('modal.geotiffCache.deleteConfirm', { file }),
        confirmLabel: t('modal.geotiffCache.delete'),
    });
    if (!confirmed) return;

    const btn = button instanceof HTMLElement ? button : null;
    const status = document.getElementById('geotiff-cache-status');
    if (btn) btn.disabled = true;
    if (status) status.textContent = t('modal.geotiffCache.deleting');
    try {
        const data = await apiDeleteJson(`${ADMIN_GEOTIFF_CACHE_URL}/${encodeURIComponent(file)}`);
        if (data.status !== 'ok') {
            throw new Error(data.error || t('modal.geotiffCache.deleteError'));
        }
        if (selectedGeotiffCacheFile === file) {
            selectedGeotiffCacheFile = null;
        }
        await loadGeotiffCacheStatus();
    } catch (err) {
        if (btn) btn.disabled = false;
        if (status) status.textContent = apiErrorMessage(err, t('modal.geotiffCache.deleteError'));
    }
}

function handleGeotiffCacheListClick(event) {
    const target = event.target instanceof Element ? event.target : null;
    if (!target) return;
    const deleteButton = target.closest('.geotiff-cache-delete');
    if (deleteButton) {
        event.preventDefault();
        event.stopPropagation();
        deleteGeotiffCacheItem(deleteButton.dataset.file, deleteButton);
        return;
    }
    const item = target.closest('.geotiff-cache-item');
    if (!item) return;
    selectGeotiffCacheItem(item.dataset.file, { pan: true, openPopup: true });
}

function handleGeotiffCacheListKeydown(event) {
    const target = event.target instanceof Element ? event.target : null;
    if (!target || target.closest('.geotiff-cache-delete')) return;
    if (event.key !== 'Enter' && event.key !== ' ') return;
    const item = target.closest('.geotiff-cache-item');
    if (!item) return;
    event.preventDefault();
    selectGeotiffCacheItem(item.dataset.file, { pan: true, openPopup: true });
}

document.getElementById('modal-geotiff-cache')?.addEventListener('modalclose', clearGeotiffCacheLayer);
document.getElementById('geotiff-cache-list')?.addEventListener('click', handleGeotiffCacheListClick);
document.getElementById('geotiff-cache-list')?.addEventListener('keydown', handleGeotiffCacheListKeydown);
