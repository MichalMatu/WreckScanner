let wreckReviewItems = [];
let wreckReviewSearchTimer = null;
let activeWreckReview = null;

function wreckReviewStatusLabel(status) {
    if (status === 'approved') return t('modal.wreckReview.approved');
    if (status === 'rejected') return t('modal.wreckReview.rejected');
    return t('modal.wreckReview.pending');
}

function wreckReviewSearchText(item) {
    return [
        item?.id,
        item?.source,
        item?.public_review_status,
        item?.lat,
        item?.lon,
        item?.created_at,
        item?.updated_at,
    ].map(value => String(value || '').toLowerCase()).join(' ');
}

function renderWreckReviewQueue() {
    const list = document.getElementById('wreck-review-list');
    if (!list) return;
    if (!wreckReviewItems.length) {
        list.innerHTML = `<p class="modal-hint" style="padding:10px">${escapeHtml(t('modal.wreckReview.noItems'))}</p>`;
        renderWreckReviewDetail(null);
        return;
    }
    list.innerHTML = wreckReviewItems.map(item => {
        const id = safeWreckId(item.id);
        const active = activeWreckReview?.id === item.id;
        const coords = [Number(item.lat).toFixed(6), Number(item.lon).toFixed(6)].join(', ');
        return `
            <button type="button" class="photo-review-item ${active ? 'is-active' : ''}" onclick="selectWreckReview('${escapeHtml(id)}')">
                <strong>${escapeHtml(id || t('modal.wreckReview.unknownCase'))}</strong>
                <span class="photo-review-pill">${escapeHtml(wreckReviewStatusLabel(item.public_review_status))}</span>
                <span>${escapeHtml(item.source || '-')} · ${escapeHtml(coords)}</span>
            </button>
        `;
    }).join('');
}

function wreckReviewLinks(item) {
    const links = item?.links || {};
    return [
        popupCompactLink(item?.folder_url, t('wreck.openCaseShort'), t('wreck.openFolder')),
        popupCompactLink(links.street_view, 'SV', t('popup.streetView')),
        popupCompactLink(links.google_maps_satellite, 'Sat', t('popup.gmapsSat')),
        popupCompactLink(links.geoportal, 'Geoportal', t('popup.geoportal')),
    ].filter(Boolean).join('');
}

function renderWreckReviewDetail(item = activeWreckReview) {
    const detail = document.getElementById('wreck-review-detail');
    if (!detail) return;
    if (!item) {
        detail.innerHTML = `<p class="modal-hint" id="wreck-review-empty">${escapeHtml(t('modal.wreckReview.empty'))}</p>`;
        return;
    }
    const lat = Number(item.lat);
    const lon = Number(item.lon);
    const links = wreckReviewLinks(item);
    detail.innerHTML = `
        <h3>${escapeHtml(item.id || t('modal.wreckReview.unknownCase'))}</h3>
        <div class="wreck-review-facts">
            <span>${escapeHtml(t('modal.wreckReview.status'))}: ${escapeHtml(wreckReviewStatusLabel(item.public_review_status))}</span>
            <span>${escapeHtml(t('modal.wreckReview.coords'))}: ${lat.toFixed(6)}, ${lon.toFixed(6)}</span>
            <span>${escapeHtml(t('modal.wreckReview.source'))}: ${escapeHtml(item.source || '-')}</span>
            <span>${escapeHtml(t('modal.wreckReview.evidenceCount'))}: ${Number(item.evidence_count || 0)}</span>
            <span>${escapeHtml(t('modal.wreckReview.photoCount'))}: ${Number(item.photo_count || 0)}</span>
            <span>${escapeHtml(t('modal.wreckReview.updatedAt'))}: ${escapeHtml(item.updated_at || item.created_at || '-')}</span>
        </div>
        ${links ? `<div class="wreck-review-links">${links}</div>` : ''}
    `;
}

function selectWreckReview(wreckId) {
    const id = safeWreckId(wreckId);
    activeWreckReview = wreckReviewItems.find(item => item.id === id) || null;
    renderWreckReviewQueue();
    renderWreckReviewDetail(activeWreckReview);
}

async function openWreckReviewModal() {
    if (!(await ensureAdmin())) return;
    const filter = document.getElementById('wreck-review-filter');
    const search = document.getElementById('wreck-review-search');
    if (filter) filter.value = 'pending';
    if (search) search.value = '';
    openModal('modal-wreck-review');
    await loadWreckReviewQueue();
}

async function loadWreckReviewQueue() {
    if (!adminAuthenticated && !(await ensureAdmin())) return;
    const filter = document.getElementById('wreck-review-filter')?.value || 'pending';
    const query = (document.getElementById('wreck-review-search')?.value || '').trim().toLowerCase();
    const status = document.getElementById('wreck-review-status');
    if (status) status.textContent = t('modal.wreckReview.loading');
    try {
        const params = new URLSearchParams({ status: filter, ts: String(Date.now()) });
        const data = await apiJson(`${ADMIN_WRECKS_URL}?${params.toString()}`, { cache: 'no-store' });
        if (data.status !== 'ok') {
            throw new Error(data.error || t('modal.wreckReview.loadError'));
        }
        const items = Array.isArray(data.wrecks) ? data.wrecks : [];
        wreckReviewItems = query ? items.filter(item => wreckReviewSearchText(item).includes(query)) : items;
        activeWreckReview = null;
        renderWreckReviewQueue();
        if (wreckReviewItems[0]) selectWreckReview(wreckReviewItems[0].id);
        if (status) status.textContent = '';
    } catch (err) {
        if (status) status.textContent = apiErrorMessage(err, t('modal.wreckReview.loadError'));
    }
}

document.getElementById('wreck-review-search')?.addEventListener('input', () => {
    if (wreckReviewSearchTimer) clearTimeout(wreckReviewSearchTimer);
    wreckReviewSearchTimer = setTimeout(loadWreckReviewQueue, 250);
});

async function saveWreckReviewStatus(publicReviewStatus) {
    if (!(await ensureAdmin())) return;
    const id = safeWreckId(activeWreckReview?.id);
    if (!id) return;
    const status = document.getElementById('wreck-review-status');
    if (status) status.textContent = t('modal.wreckReview.saving');
    try {
        const data = await apiPatchJson(`${ADMIN_WRECKS_URL}/${encodeURIComponent(id)}/review`, {
            public_review_status: publicReviewStatus,
        });
        if (data.status !== 'ok') {
            throw new Error(data.error || t('modal.wreckReview.saveError'));
        }
        await loadSavedWrecks();
        await loadWreckReviewQueue();
        if (status) status.textContent = t('modal.wreckReview.saved');
    } catch (err) {
        if (status) status.textContent = apiErrorMessage(err, t('modal.wreckReview.saveError'));
    }
}

async function deleteWreckReviewItem() {
    if (!(await ensureAdmin())) return;
    const id = safeWreckId(activeWreckReview?.id);
    if (!id) return;
    const confirmed = await confirmAction({
        title: t('wreck.deleteTitle'),
        message: t('wreck.deleteConfirm'),
        confirmLabel: t('wreck.delete'),
    });
    if (!confirmed) return;
    const status = document.getElementById('wreck-review-status');
    if (status) status.textContent = t('wreck.deleting');
    try {
        const data = await apiDeleteJson(`${WRECKS_URL}/${encodeURIComponent(id)}`);
        if (data.status !== 'ok') {
            throw new Error(data.error || t('wreck.deleteError'));
        }
        await loadSavedWrecks();
        await loadWreckReviewQueue();
        if (status) status.textContent = t('wreck.deleted');
    } catch (err) {
        if (status) status.textContent = apiErrorMessage(err, t('wreck.deleteError'));
    }
}

function focusWreckReviewOnMap() {
    const lat = Number(activeWreckReview?.lat);
    const lon = Number(activeWreckReview?.lon);
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) return;
    closeModal(document.getElementById('modal-wreck-review'));
    map.setView([lat, lon], Math.max(map.getZoom(), 19));
}
