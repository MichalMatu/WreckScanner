let privacyRequestItems = [];
let activePrivacyRequest = null;
let privacyQueueRequestRevision = 0;
let privacyQueueAbortController = null;
let privacySaveInFlight = false;

function privacyRequestStatusLabel(status) {
    if (status === 'in_progress') return t('modal.privacyRequests.inProgress');
    if (status === 'done') return t('modal.privacyRequests.done');
    if (status === 'rejected') return t('modal.privacyRequests.rejected');
    return t('modal.privacyRequests.new');
}

function renderPrivacyRequestQueue() {
    const list = document.getElementById('privacy-request-list');
    if (!list) return;
    if (!privacyRequestItems.length) {
        list.innerHTML = `<p class="modal-hint" style="padding:10px">${escapeHtml(t('modal.privacyRequests.noItems'))}</p>`;
        return;
    }
    list.innerHTML = privacyRequestItems.map(item => {
        const active = activePrivacyRequest?.id === item.id;
        const title = item.target || item.id;
        return `
            <button type="button" class="privacy-request-item ${active ? 'is-active' : ''}" onclick="selectPrivacyRequest('${escapeHtml(item.id)}')">
                <strong>${escapeHtml(title)}</strong>
                <span class="photo-review-pill">${escapeHtml(privacyRequestStatusLabel(item.status))}</span>
                <span>${escapeHtml(item.email || '')}</span>
                <span>${escapeHtml(item.updated_at || item.created_at || '')}</span>
            </button>
        `;
    }).join('');
}

function privacyRequestTargetHtml(target) {
    const text = String(target || '').trim();
    if (/^https?:\/\//i.test(text)) {
        const safeHref = escapeHtml(text);
        return `<a href="${safeHref}" target="_blank" rel="noopener">${safeHref}</a>`;
    }
    return escapeHtml(text);
}

function renderPrivacyRequestDetail() {
    const detail = document.getElementById('privacy-request-detail');
    if (!detail) return;
    if (!activePrivacyRequest) {
        detail.innerHTML = `<p class="modal-hint">${escapeHtml(t('modal.privacyRequests.empty'))}</p>`;
        return;
    }
    detail.innerHTML = `
        <div class="privacy-request-meta">
            <label class="report-field">
                <span>${escapeHtml(t('modal.privacyRequests.status'))}</span>
                <select class="modal-input" id="privacy-request-status-select">
                    <option value="new" ${activePrivacyRequest.status === 'new' ? 'selected' : ''}>${escapeHtml(t('modal.privacyRequests.new'))}</option>
                    <option value="in_progress" ${activePrivacyRequest.status === 'in_progress' ? 'selected' : ''}>${escapeHtml(t('modal.privacyRequests.inProgress'))}</option>
                    <option value="done" ${activePrivacyRequest.status === 'done' ? 'selected' : ''}>${escapeHtml(t('modal.privacyRequests.done'))}</option>
                    <option value="rejected" ${activePrivacyRequest.status === 'rejected' ? 'selected' : ''}>${escapeHtml(t('modal.privacyRequests.rejected'))}</option>
                </select>
            </label>
            <div class="privacy-request-facts">
                <span><b>${escapeHtml(t('modal.privacyRequests.email'))}</b> ${escapeHtml(activePrivacyRequest.email || '')}</span>
                <span><b>${escapeHtml(t('modal.privacyRequests.createdAt'))}</b> ${escapeHtml(activePrivacyRequest.created_at || '')}</span>
                <span><b>${escapeHtml(t('modal.privacyRequests.updatedAt'))}</b> ${escapeHtml(activePrivacyRequest.updated_at || '')}</span>
            </div>
        </div>
        <section class="modal-section privacy-request-section">
            <label class="modal-label">${escapeHtml(t('modal.privacyRequests.target'))}</label>
            <p class="privacy-request-text">${privacyRequestTargetHtml(activePrivacyRequest.target)}</p>
        </section>
        <section class="modal-section privacy-request-section">
            <label class="modal-label">${escapeHtml(t('modal.privacyRequests.reason'))}</label>
            <p class="privacy-request-text">${escapeHtml(activePrivacyRequest.reason || '')}</p>
        </section>
        <label class="report-field">
            <span>${escapeHtml(t('modal.privacyRequests.adminNote'))}</span>
            <textarea id="privacy-request-admin-note" rows="6" maxlength="4000">${escapeHtml(activePrivacyRequest.admin_note || '')}</textarea>
        </label>
        <div class="privacy-request-actions">
            <button type="button" class="btn-download report-submit-btn" id="privacy-request-save"
                onclick="savePrivacyRequestUpdate()" ${privacySaveInFlight ? 'disabled' : ''}>
                <span>${escapeHtml(t('modal.privacyRequests.save'))}</span>
            </button>
        </div>
    `;
}

function selectPrivacyRequest(requestId) {
    activePrivacyRequest = privacyRequestItems.find(item => item.id === requestId) || null;
    renderPrivacyRequestQueue();
    renderPrivacyRequestDetail();
}

async function openPrivacyRequestsModal() {
    if (!(await ensureAdmin())) return;
    openAdminChildModal('modal-privacy-requests');
    await loadPrivacyRequestQueue();
}

async function loadPrivacyRequestQueue(options = {}) {
    if (!adminAuthenticated && !(await ensureAdmin())) return;
    const requestRevision = ++privacyQueueRequestRevision;
    privacyQueueAbortController?.abort();
    const requestController = new AbortController();
    privacyQueueAbortController = requestController;
    const filter = document.getElementById('privacy-request-filter')?.value || 'new';
    const preferredRequestId = options.preferredRequestId ?? activePrivacyRequest?.id ?? null;
    const status = document.getElementById('privacy-request-status');
    if (status && options.announceLoading !== false) status.textContent = t('modal.privacyRequests.loading');
    try {
        const data = await apiJson(`${ADMIN_PRIVACY_REQUESTS_URL}?status=${encodeURIComponent(filter)}&ts=${Date.now()}`, {
            cache: 'no-store',
            signal: requestController.signal,
        });
        if (requestRevision !== privacyQueueRequestRevision) return;
        if (data.status !== 'ok') {
            throw new Error(data.error || t('modal.privacyRequests.loadError'));
        }
        privacyRequestItems = Array.isArray(data.requests) ? data.requests : [];
        activePrivacyRequest = privacyRequestItems.find(item => item.id === preferredRequestId)
            || privacyRequestItems[0]
            || null;
        renderPrivacyRequestQueue();
        renderPrivacyRequestDetail();
        if (status) status.textContent = '';
    } catch (err) {
        if (requestRevision !== privacyQueueRequestRevision || err?.payload?.code === 'cancelled') return;
        if (status) status.textContent = apiErrorMessage(err, t('modal.privacyRequests.loadError'));
    } finally {
        if (privacyQueueAbortController === requestController) privacyQueueAbortController = null;
    }
}

async function savePrivacyRequestUpdate() {
    if (!activePrivacyRequest?.id || privacySaveInFlight) return;
    const savedRequestId = activePrivacyRequest.id;
    const statusEl = document.getElementById('privacy-request-status');
    const statusValue = document.getElementById('privacy-request-status-select')?.value || 'new';
    const adminNote = document.getElementById('privacy-request-admin-note')?.value || '';
    privacySaveInFlight = true;
    const saveButton = document.getElementById('privacy-request-save');
    if (saveButton) saveButton.disabled = true;
    if (statusEl) statusEl.textContent = t('modal.privacyRequests.saving');
    try {
        const data = await apiPatchJson(`${ADMIN_PRIVACY_REQUESTS_URL}/${encodeURIComponent(savedRequestId)}`, {
            status: statusValue,
            admin_note: adminNote,
        });
        if (data.status !== 'ok') {
            throw new Error(data.error || t('modal.privacyRequests.saveError'));
        }
        await loadPrivacyRequestQueue({
            preferredRequestId: data.request?.id || savedRequestId,
            announceLoading: false,
        });
        if (statusEl) statusEl.textContent = t('modal.privacyRequests.saved');
    } catch (err) {
        if (statusEl) statusEl.textContent = apiErrorMessage(err, t('modal.privacyRequests.saveError'));
    } finally {
        privacySaveInFlight = false;
        const currentSaveButton = document.getElementById('privacy-request-save');
        if (currentSaveButton) currentSaveButton.disabled = false;
    }
}

document.getElementById('modal-privacy-requests')?.addEventListener('modalclose', () => {
    privacyQueueRequestRevision += 1;
    privacyQueueAbortController?.abort();
    privacyQueueAbortController = null;
});
