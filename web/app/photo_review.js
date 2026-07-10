let photoReviewItems = [];
let photoReviewSearchTimer = null;
let photoReviewExactPhotoIds = [];
let photoReviewMode = 'admin';
let ownerPhotoReviewToken = '';
let ownerPhotoReviewObjectUrl = null;
let ownerFieldPhotoIds = [];
let ownerPhotoReviewReturnToSummary = false;
let activePhotoReview = null;
let photoReviewImage = null;
let photoReviewRedactions = [];
let activePhotoReviewRedactionIndex = -1;
let photoReviewDraftRect = null;
let photoReviewDrawing = false;
let photoReviewSelectionRequest = 0;
let photoReviewQueueRequest = 0;
let photoReviewActionInFlight = false;
let photoReviewSavedSnapshot = null;
let photoReviewLoadedFilter = 'pending';
let photoReviewLoadedQuery = '';

async function openPhotoReviewForFieldPhotoGroup(encodedPhotoIds) {
    if (!(await ensureAdmin())) return;
    setPhotoReviewMode('admin');
    const photoIds = decodeFieldPhotoIds(encodedPhotoIds);
    if (!photoIds.length) return;
    photoReviewExactPhotoIds = photoIds;
    openModal('modal-photo-review');
    const filter = document.getElementById('photo-review-filter');
    const search = document.getElementById('photo-review-search');
    if (filter) filter.value = 'all';
    if (search) search.value = photoIds.join(', ');
    await loadPhotoReviewQueue();
}

function setPhotoReviewMode(mode = 'admin') {
    photoReviewMode = mode === 'owner' ? 'owner' : 'admin';
    const ownerMode = photoReviewMode === 'owner';
    if (!ownerMode) {
        ownerPhotoReviewToken = '';
        ownerFieldPhotoIds = [];
        ownerPhotoReviewReturnToSummary = false;
        revokeOwnerPhotoReviewObjectUrl();
    }
    const title = document.getElementById('photo-review-title');
    const controls = document.getElementById('photo-review-controls');
    const saveButton = document.getElementById('photo-review-save');
    const saveLabel = document.getElementById('photo-review-save-label');
    if (title) title.textContent = ownerMode ? t('modal.photoReview.ownerTitle') : t('modal.photoReview.title');
    if (controls) controls.hidden = ownerMode;
    if (saveButton) {
        const saveText = t(ownerMode ? 'modal.photoReview.saveOwner' : 'modal.photoReview.savePending');
        saveButton.title = saveText;
        saveButton.setAttribute('aria-label', saveText);
    }
    if (saveLabel) {
        saveLabel.textContent = t(ownerMode ? 'modal.photoReview.saveOwnerShort' : 'modal.photoReview.savePendingShort');
    }
    document.querySelectorAll('#modal-photo-review .admin-review-only').forEach(button => {
        button.hidden = ownerMode || (button.id === 'photo-review-delete');
    });
    updatePhotoReviewReturnAction();
    updatePhotoReviewDeleteAction();
    updatePhotoReviewVehicleResolutionAction();
}

function updatePhotoReviewReturnAction() {
    const button = document.getElementById('photo-review-return-summary');
    const closeButton = document.getElementById('photo-review-close');
    const summaryReturnFlow = photoReviewMode === 'owner' && ownerPhotoReviewReturnToSummary;
    if (button) button.hidden = !summaryReturnFlow;
    if (closeButton) closeButton.hidden = summaryReturnFlow;
}

function photoReviewRequiresSummaryReturn() {
    const modal = document.getElementById('modal-photo-review');
    return Boolean(modal && !modal.hidden && photoReviewMode === 'owner' && ownerPhotoReviewReturnToSummary);
}

async function closePhotoReviewModal(target) {
    if (!(await confirmPhotoReviewDiscard())) return;
    if (photoReviewRequiresSummaryReturn()) {
        await returnPhotoReviewToFieldPhotoSummary({ skipDirtyGuard: true });
        return;
    }
    closeModal(target instanceof Element ? target : document.getElementById('modal-photo-review'));
}

async function handlePhotoReviewBackdropClose(target) {
    if (photoReviewRequiresSummaryReturn()) return;
    if (!(await confirmPhotoReviewDiscard())) return;
    closeModal(target);
}

function openFieldPhotoOwnerEditor(encodedPhotoIds) {
    const photoIds = decodeFieldPhotoIds(encodedPhotoIds);
    if (!photoIds.length) return;
    ownerFieldPhotoIds = photoIds;
    ownerPhotoReviewToken = '';
    const form = document.getElementById('field-photo-owner-form');
    const status = document.getElementById('field-photo-owner-status');
    const submit = document.getElementById('field-photo-owner-submit');
    form?.reset();
    if (status) status.textContent = '';
    if (submit) submit.disabled = false;
    openModal('modal-field-photo-owner');
    requestAnimationFrame(() => document.getElementById('field-photo-owner-token')?.focus());
}

async function openFieldPhotoOwnerReviewWithToken(photoIds, token, options = {}) {
    const normalizedPhotoIds = (Array.isArray(photoIds) ? photoIds : [])
        .map(safeFieldPhotoId)
        .filter(Boolean);
    const normalizedToken = String(token || '').trim();
    const tokenError = validateFieldPhotoEditToken(normalizedToken, { required: true });
    if (!normalizedPhotoIds.length) throw new Error(t('modal.fieldPhotoOwner.unlockError'));
    if (tokenError) throw new Error(tokenError);

    const data = await apiPostJson(`${FIELD_PHOTOS_URL}/owner-claim`, {
        photo_ids: normalizedPhotoIds,
        edit_token: normalizedToken,
    });
    if (data.status !== 'ok') {
        throw new Error(data.error || t('modal.fieldPhotoOwner.unlockError'));
    }
    photoReviewItems = Array.isArray(data.photos) ? data.photos : [];
    if (!photoReviewItems.length) throw new Error(t('modal.fieldPhotoOwner.unlockError'));
    ownerFieldPhotoIds = normalizedPhotoIds;
    ownerPhotoReviewToken = normalizedToken;
    photoReviewExactPhotoIds = [];
    activePhotoReview = null;
    photoReviewImage = null;
    photoReviewRedactions = [];
    activePhotoReviewRedactionIndex = -1;
    photoReviewDraftRect = null;
    ownerPhotoReviewReturnToSummary = Boolean(options.returnToFieldPhotoSummary);
    if (options.sourceModalId) closeModal(document.getElementById(options.sourceModalId));
    setPhotoReviewMode('owner');
    openModal('modal-photo-review');
    renderPhotoReviewQueue();
    clearPhotoReviewCanvas();
    selectPhotoReview(photoReviewItems[0].id);
}

async function returnPhotoReviewToFieldPhotoSummary(options = {}) {
    if (photoReviewMode !== 'owner' || !ownerPhotoReviewReturnToSummary) return;
    if (!options.skipDirtyGuard && !(await confirmPhotoReviewDiscard())) return;
    closeModal(document.getElementById('modal-photo-review'));
    openModal('modal-field-photo-thanks');
}

async function submitFieldPhotoOwnerToken(event) {
    event.preventDefault();
    const token = String(document.getElementById('field-photo-owner-token')?.value || '').trim();
    const status = document.getElementById('field-photo-owner-status');
    const submit = document.getElementById('field-photo-owner-submit');
    const tokenError = validateFieldPhotoEditToken(token, { required: true });
    if (tokenError) {
        if (status) status.textContent = tokenError;
        return;
    }
    if (submit) submit.disabled = true;
    if (status) status.textContent = t('modal.fieldPhotoOwner.loading');
    try {
        await openFieldPhotoOwnerReviewWithToken(ownerFieldPhotoIds, token, { sourceModalId: 'modal-field-photo-owner' });
    } catch (err) {
        if (status) status.textContent = apiErrorMessage(err, t('modal.fieldPhotoOwner.unlockError'));
    } finally {
        if (submit) submit.disabled = false;
    }
}

function photoReviewStatusLabel(status) {
    if (status === 'approved') return t('modal.photoReview.approved');
    if (status === 'rejected') return t('modal.photoReview.rejected');
    return t('modal.photoReview.pending');
}

function setPhotoReviewStatusMessage(message = '') {
    const status = document.getElementById('photo-review-status');
    if (!status) return;
    const text = String(message || '').trim();
    status.textContent = text;
    status.hidden = !text;
}

function photoReviewQueueDisplay(item, index = 0) {
    const originalName = String(item?.original_filename || '').trim();
    const technicalId = String(item?.photo_id || item?.id || '').trim();
    const primaryLabel = item?.captured_at || originalName || technicalId;
    const display = photoPreviewDisplay({ source: item?.scope || 'field', label: primaryLabel }, index);
    const detailParts = [originalName, technicalId]
        .filter((value, partIndex, parts) => value && value !== display.name && parts.indexOf(value) === partIndex);
    return {
        title: display.name || t('modal.photoPreview.photoNumber', { n: index + 1 }),
        detail: detailParts.join(' · '),
    };
}

function photoReviewEndpoint(item) {
    if (!item) return null;
    if (photoReviewMode === 'owner' && item.scope === 'field') {
        return `${FIELD_PHOTOS_URL}/${encodeURIComponent(item.photo_id)}/owner-review`;
    }
    if (item.scope === 'field') {
        return `${ADMIN_PHOTOS_URL}/field/${encodeURIComponent(item.photo_id)}/review`;
    }
    return null;
}

function photoReviewDeleteEndpoint(item) {
    if (!item) return null;
    if (item.scope === 'field') {
        return `${ADMIN_PHOTOS_URL}/field/${encodeURIComponent(item.photo_id)}`;
    }
    return null;
}

function updatePhotoReviewDeleteAction() {
    const button = document.getElementById('photo-review-delete');
    if (!button) return;
    if (photoReviewMode === 'owner') {
        button.hidden = true;
        button.disabled = true;
        return;
    }
    const canDelete = activePhotoReview?.public_review_status === 'rejected' && Boolean(photoReviewDeleteEndpoint(activePhotoReview));
    button.hidden = !canDelete;
    button.disabled = photoReviewActionInFlight || !canDelete;
}

function photoReviewActionControls() {
    const modal = document.getElementById('modal-photo-review');
    if (!modal) return [];
    return Array.from(modal.querySelectorAll('.photo-review-actions button, .photo-review-list button, input[name="photo-review-vehicle-insurance-status"]'));
}

function updatePhotoReviewActionLock() {
    photoReviewActionControls().forEach(control => {
        control.disabled = photoReviewActionInFlight;
    });
    if (!photoReviewActionInFlight) {
        updatePhotoReviewDeleteAction();
        updatePhotoReviewVehicleResolutionAction();
    }
}

function setPhotoReviewActionInFlight(inFlight) {
    photoReviewActionInFlight = Boolean(inFlight);
    updatePhotoReviewActionLock();
}

function renderPhotoReviewQueue() {
    const list = document.getElementById('photo-review-list');
    if (!list) return;
    if (!photoReviewItems.length) {
        list.innerHTML = `<p class="modal-hint" style="padding:10px">${escapeHtml(t('modal.photoReview.noItems'))}</p>`;
        return;
    }
    list.innerHTML = photoReviewItems.map((item, index) => {
        const active = activePhotoReview?.id === item.id;
        const display = photoReviewQueueDisplay(item, index);
        const detailHtml = display.detail
            ? `<span class="photo-review-detail">${escapeHtml(display.detail)}</span>`
            : '';
        const resolutionPill = photoReviewItemIsRemoved(item)
            ? `<span class="photo-review-pill">${escapeHtml(t('vehicle.resolution.badgeRemoved'))}</span>`
            : '';
        return `
            <button type="button"
                class="photo-review-item ${active ? 'is-active' : ''}"
                data-photo-review-id="${escapeHtml(item.id)}"
                onclick="selectPhotoReview('${escapeHtml(item.id)}')">
                <strong>${escapeHtml(display.title)}</strong>
                <span class="photo-review-pill">${escapeHtml(photoReviewStatusLabel(item.public_review_status))}</span>
                ${resolutionPill}
                ${detailHtml}
            </button>
        `;
    }).join('');
    updatePhotoReviewActionLock();
}

function photoReviewActiveIndex(itemId = activePhotoReview?.id) {
    return photoReviewItems.findIndex(item => item.id === itemId);
}

function photoReviewSelectionAfterReload(items, preferredId, fallbackIndex) {
    if (preferredId && items.some(item => item.id === preferredId)) return preferredId;
    if (!items.length) return null;
    const boundedIndex = Number.isInteger(fallbackIndex)
        ? Math.max(0, Math.min(items.length - 1, fallbackIndex))
        : 0;
    return items[boundedIndex]?.id || null;
}

function photoReviewItemButton(itemId) {
    const list = document.getElementById('photo-review-list');
    if (!list) return null;
    return Array.from(list.querySelectorAll('.photo-review-item'))
        .find(button => button.dataset.photoReviewId === itemId) || null;
}

function focusPhotoReviewItem(itemId) {
    const button = photoReviewItemButton(itemId);
    if (!button) return;
    button.focus({ preventScroll: true });
    button.scrollIntoView({ block: 'nearest' });
}

function photoReviewKeyboardTargetAllowsNavigation(target) {
    const list = document.getElementById('photo-review-list');
    if (!(target instanceof Element)) return true;
    if (list && list.contains(target)) return true;
    return target === document.body || target === document.documentElement;
}

function movePhotoReviewSelection(targetIndex) {
    if (!photoReviewItems.length) return false;
    const boundedIndex = Math.max(0, Math.min(photoReviewItems.length - 1, targetIndex));
    const item = photoReviewItems[boundedIndex];
    if (!item) return false;
    if (activePhotoReview?.id === item.id) {
        focusPhotoReviewItem(item.id);
        return true;
    }
    selectPhotoReview(item.id, { focusListItem: true });
    return true;
}

function stepPhotoReviewSelection(delta) {
    const activeIndex = photoReviewActiveIndex();
    const baseIndex = activeIndex >= 0
        ? activeIndex
        : (delta > 0 ? -1 : photoReviewItems.length);
    return movePhotoReviewSelection(baseIndex + delta);
}

async function openPhotoReviewModal() {
    if (!(await ensureAdmin())) return;
    setPhotoReviewMode('admin');
    photoReviewExactPhotoIds = [];
    const filter = document.getElementById('photo-review-filter');
    const search = document.getElementById('photo-review-search');
    if (filter) filter.value = 'pending';
    if (search) search.value = '';
    openAdminChildModal('modal-photo-review');
    await loadPhotoReviewQueue();
}

async function loadPhotoReviewQueue(options = {}) {
    if (photoReviewMode !== 'admin') return;
    if (!adminAuthenticated && !(await ensureAdmin())) return;
    if (!options.skipDirtyGuard && !(await confirmPhotoReviewDiscard())) {
        const filterControl = document.getElementById('photo-review-filter');
        const searchControl = document.getElementById('photo-review-search');
        if (filterControl) filterControl.value = photoReviewLoadedFilter;
        if (searchControl) searchControl.value = photoReviewLoadedQuery;
        return;
    }
    const queueRequest = ++photoReviewQueueRequest;
    const isCurrentQueueRequest = () => queueRequest === photoReviewQueueRequest;
    const previousActiveId = options.preferredPhotoId ?? activePhotoReview?.id ?? null;
    const previousActiveIndex = Number.isInteger(options.fallbackIndex)
        ? options.fallbackIndex
        : photoReviewActiveIndex(previousActiveId);
    const list = document.getElementById('photo-review-list');
    const preservedScrollTop = options.preserveScroll ? list?.scrollTop : null;
    const filter = document.getElementById('photo-review-filter')?.value || 'pending';
    const query = document.getElementById('photo-review-search')?.value || '';
    setPhotoReviewStatusMessage(t('modal.photoReview.loading'));
    try {
        const params = new URLSearchParams({
            status: filter,
            q: photoReviewExactPhotoIds.length ? '' : query,
            ts: String(Date.now()),
        });
        if (photoReviewExactPhotoIds.length) {
            params.set('ids', photoReviewExactPhotoIds.join(','));
        }
        const data = await apiJson(`${ADMIN_PHOTOS_URL}?${params.toString()}`, { cache: 'no-store' });
        if (!isCurrentQueueRequest()) return;
        if (data.status !== 'ok') {
            throw new Error(data.error || t('modal.photoReview.loadError'));
        }
        const nextItems = Array.isArray(data.photos) ? data.photos : [];
        const nextActiveId = photoReviewSelectionAfterReload(nextItems, previousActiveId, previousActiveIndex);
        photoReviewItems = nextItems;
        activePhotoReview = null;
        photoReviewImage = null;
        photoReviewRedactions = [];
        activePhotoReviewRedactionIndex = -1;
        updatePhotoReviewDeleteAction();
        renderPhotoReviewQueue();
        clearPhotoReviewCanvas();
        photoReviewSavedSnapshot = null;
        photoReviewLoadedFilter = filter;
        photoReviewLoadedQuery = query;
        if (Number.isFinite(preservedScrollTop)) {
            const nextList = document.getElementById('photo-review-list');
            if (nextList) nextList.scrollTop = preservedScrollTop;
        }
        if (nextActiveId) selectPhotoReview(nextActiveId, { preserveScrollTop: preservedScrollTop });
        setPhotoReviewStatusMessage();
    } catch (err) {
        if (!isCurrentQueueRequest()) return;
        setPhotoReviewStatusMessage(apiErrorMessage(err, t('modal.photoReview.loadError')));
    }
}

document.getElementById('photo-review-search')?.addEventListener('input', () => {
    photoReviewExactPhotoIds = [];
    if (photoReviewSearchTimer) clearTimeout(photoReviewSearchTimer);
    photoReviewSearchTimer = setTimeout(loadPhotoReviewQueue, 250);
});

document.addEventListener('keydown', event => {
    if (topOpenModalBackdrop()?.id !== 'modal-photo-review') return;
    if (event.altKey || event.ctrlKey || event.metaKey) return;
    if (!photoReviewKeyboardTargetAllowsNavigation(event.target)) return;
    let handled = false;
    if (event.key === 'ArrowDown') {
        handled = stepPhotoReviewSelection(1);
    } else if (event.key === 'ArrowUp') {
        handled = stepPhotoReviewSelection(-1);
    } else if (event.key === 'Home') {
        handled = movePhotoReviewSelection(0);
    } else if (event.key === 'End') {
        handled = movePhotoReviewSelection(photoReviewItems.length - 1);
    }
    if (!handled) return;
    event.preventDefault();
    event.stopPropagation();
});

photoReviewVehicleInsuranceInputs().forEach(input => {
    input.addEventListener('change', updatePhotoReviewVehicleInsuranceCheckedText);
});

document.getElementById('modal-photo-review')?.addEventListener('modalclose', () => {
    photoReviewSavedSnapshot = null;
    revokeOwnerPhotoReviewObjectUrl();
});

document.addEventListener('keydown', event => {
    const modal = document.getElementById('modal-photo-review');
    if (event.key !== 'Escape' || !modal || modal.hidden || topOpenModalBackdrop() !== modal) return;
    const confirmModal = document.getElementById('modal-confirm');
    const adminModal = document.getElementById('modal-admin-login');
    if ((confirmModal && !confirmModal.hidden) || (adminModal && !adminModal.hidden)) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    closePhotoReviewModal();
}, true);

function clearPhotoReviewCanvas() {
    const canvas = document.getElementById('photo-review-canvas');
    const empty = document.getElementById('photo-review-empty');
    if (canvas) {
        canvas.style.display = 'none';
        clearPhotoReviewCursorState(canvas);
        const ctx = canvas.getContext('2d');
        ctx?.clearRect(0, 0, canvas.width, canvas.height);
    }
    if (empty) empty.hidden = false;
    updatePhotoReviewVehicleInsuranceUi();
    updatePhotoReviewDeleteAction();
    updatePhotoReviewVehicleResolutionAction();
}

function revokeOwnerPhotoReviewObjectUrl() {
    if (!ownerPhotoReviewObjectUrl) return;
    URL.revokeObjectURL(ownerPhotoReviewObjectUrl);
    ownerPhotoReviewObjectUrl = null;
}

async function photoReviewOriginalImageSrc(item, isCurrentSelection = () => true) {
    if (photoReviewMode !== 'owner') {
        return `${item.original_image}?ts=${Date.now()}`;
    }
    const blob = await apiBlob(item.original_image, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ edit_token: ownerPhotoReviewToken }),
    });
    if (!isCurrentSelection()) return null;
    revokeOwnerPhotoReviewObjectUrl();
    ownerPhotoReviewObjectUrl = URL.createObjectURL(blob);
    return ownerPhotoReviewObjectUrl;
}

async function selectPhotoReview(itemId, options = {}) {
    const item = photoReviewItems.find(candidate => candidate.id === itemId);
    if (!item) return;
    if (activePhotoReview?.id !== item.id && !options.skipDirtyGuard && !(await confirmPhotoReviewDiscard())) {
        focusPhotoReviewItem(activePhotoReview?.id);
        return;
    }
    const selectionRequest = ++photoReviewSelectionRequest;
    const isCurrentSelection = () => selectionRequest === photoReviewSelectionRequest && activePhotoReview?.id === item.id;
    const list = document.getElementById('photo-review-list');
    const preservedScrollTop = Number.isFinite(options.preserveScrollTop) ? options.preserveScrollTop : null;
    activePhotoReview = item;
    updatePhotoReviewVehicleInsuranceUi();
    updatePhotoReviewVehicleResolutionAction();
    photoReviewRedactions = (Array.isArray(item.redactions) ? item.redactions : [])
        .map(normalizePhotoReviewRedaction)
        .filter(Boolean);
    activePhotoReviewRedactionIndex = photoReviewRedactions.length ? photoReviewRedactions.length - 1 : -1;
    photoReviewDraftRect = null;
    capturePhotoReviewSnapshot();
    updatePhotoReviewDeleteAction();
    updatePhotoReviewVehicleResolutionAction();
    renderPhotoReviewQueue();
    if (Number.isFinite(preservedScrollTop) && list) list.scrollTop = preservedScrollTop;
    if (options.focusListItem) focusPhotoReviewItem(item.id);
    setPhotoReviewStatusMessage(t('modal.photoReview.imageLoading'));
    const image = new Image();
    image.onload = () => {
        if (!isCurrentSelection()) return;
        photoReviewImage = image;
        const canvas = document.getElementById('photo-review-canvas');
        const empty = document.getElementById('photo-review-empty');
        if (!canvas) return;
        const maxWidth = 900;
        const scale = Math.min(1, maxWidth / Math.max(1, image.naturalWidth));
        canvas.width = Math.max(1, Math.round(image.naturalWidth * scale));
        canvas.height = Math.max(1, Math.round(image.naturalHeight * scale));
        canvas.style.aspectRatio = `${canvas.width} / ${canvas.height}`;
        canvas.style.display = 'block';
        clearPhotoReviewCursorState(canvas);
        if (empty) empty.hidden = true;
        drawPhotoReviewCanvas();
        setPhotoReviewStatusMessage();
    };
    image.onerror = () => {
        if (!isCurrentSelection()) return;
        photoReviewImage = null;
        clearPhotoReviewCanvas();
        setPhotoReviewStatusMessage(t('modal.photoReview.imageError'));
    };
    try {
        const imageSrc = await photoReviewOriginalImageSrc(item, isCurrentSelection);
        if (!imageSrc || !isCurrentSelection()) return;
        image.src = imageSrc;
    } catch (err) {
        if (!isCurrentSelection()) return;
        photoReviewImage = null;
        clearPhotoReviewCanvas();
        setPhotoReviewStatusMessage(err.message || t('modal.photoReview.imageError'));
    }
}

async function savePhotoReviewStatus(publicReviewStatus) {
    if (photoReviewActionInFlight) return;
    const endpoint = photoReviewEndpoint(activePhotoReview);
    if (!endpoint) return;
    const savedPhotoId = activePhotoReview.id;
    const savedPhotoIndex = photoReviewActiveIndex(savedPhotoId);
    const list = document.getElementById('photo-review-list');
    const savedScrollTop = list?.scrollTop;
    setPhotoReviewActionInFlight(true);
    setPhotoReviewStatusMessage(t('modal.photoReview.saving'));
    try {
        const payload = photoReviewMode === 'owner'
            ? { edit_token: ownerPhotoReviewToken, redactions: photoReviewRedactions, ...photoReviewVehicleInsurancePayload() }
            : { public_review_status: publicReviewStatus, redactions: photoReviewRedactions, ...photoReviewVehicleInsurancePayload() };
        const data = await apiPatchJson(endpoint, payload);
        if (data.status !== 'ok') {
            throw new Error(data.error || t('modal.photoReview.saveError'));
        }
        setPhotoReviewStatusMessage(photoReviewMode === 'owner'
            ? t(data.photo?.public_review_status === 'draft'
                ? 'modal.photoReview.ownerDraftSaved'
                : 'modal.photoReview.ownerSaved')
            : t('modal.photoReview.saved'));
        if (photoReviewMode === 'owner') {
            activePhotoReview.public_review_status = data.photo?.public_review_status || 'pending';
            activePhotoReview.vehicle_insurance_status = data.photo?.vehicle_insurance_status
                || photoReviewVehicleInsurancePayload().vehicle_insurance_status
                || activePhotoReview.vehicle_insurance_status;
            activePhotoReview.vehicle_insurance_checked_at = data.photo?.vehicle_insurance_checked_at
                || activePhotoReview.vehicle_insurance_checked_at;
            activePhotoReview.redactions = photoReviewRedactions;
            capturePhotoReviewSnapshot();
            renderPhotoReviewQueue();
            updatePhotoReviewVehicleInsuranceUi();
            await loadFieldPhotos();
            return;
        }
        await loadFieldPhotos();
        capturePhotoReviewSnapshot();
        await loadPhotoReviewQueue({
            preferredPhotoId: savedPhotoId,
            fallbackIndex: savedPhotoIndex,
            preserveScroll: Number.isFinite(savedScrollTop),
            skipDirtyGuard: true,
        });
    } catch (err) {
        setPhotoReviewStatusMessage(apiErrorMessage(err, t('modal.photoReview.saveError')));
    } finally {
        setPhotoReviewActionInFlight(false);
    }
}

async function deletePhotoReviewItem() {
    if (photoReviewActionInFlight) return;
    const endpoint = photoReviewDeleteEndpoint(activePhotoReview);
    if (!endpoint || activePhotoReview?.public_review_status !== 'rejected') return;
    if (!(await confirmPhotoReviewDiscard())) return;
    const deletedPhotoIndex = photoReviewActiveIndex(activePhotoReview.id);
    const list = document.getElementById('photo-review-list');
    const deletedScrollTop = list?.scrollTop;
    const confirmed = await confirmAction({
        title: t('modal.photoReview.deleteTitle'),
        message: t('modal.photoReview.deleteConfirm'),
        confirmLabel: t('modal.photoReview.delete'),
    });
    if (!confirmed) return;
    setPhotoReviewActionInFlight(true);
    setPhotoReviewStatusMessage(t('modal.photoReview.deleting'));
    try {
        const data = await apiDeleteJson(endpoint);
        if (data.status !== 'ok') {
            throw new Error(data.error || t('modal.photoReview.deleteError'));
        }
        setPhotoReviewStatusMessage(t('modal.photoReview.deleted'));
        await loadFieldPhotos();
        await loadPhotoReviewQueue({
            fallbackIndex: deletedPhotoIndex,
            preserveScroll: Number.isFinite(deletedScrollTop),
        });
    } catch (err) {
        setPhotoReviewStatusMessage(apiErrorMessage(err, t('modal.photoReview.deleteError')));
    } finally {
        setPhotoReviewActionInFlight(false);
    }
}
