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

function closePhotoReviewModal(target) {
    if (photoReviewRequiresSummaryReturn()) {
        returnPhotoReviewToFieldPhotoSummary();
        return;
    }
    closeModal(target instanceof Element ? target : document.getElementById('modal-photo-review'));
}

function handlePhotoReviewBackdropClose(target) {
    if (photoReviewRequiresSummaryReturn()) return;
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

function returnPhotoReviewToFieldPhotoSummary() {
    if (photoReviewMode !== 'owner' || !ownerPhotoReviewReturnToSummary) return;
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

function photoReviewVehicleInsuranceInputs() {
    return Array.from(document.querySelectorAll('input[name="photo-review-vehicle-insurance-status"]'));
}

function photoReviewVehicleInsuranceStatus() {
    const checked = photoReviewVehicleInsuranceInputs().find(input => input.checked);
    return vehicleInsuranceStatus(checked?.value || activePhotoReview?.vehicle_insurance_status);
}

function photoReviewVehicleInsurancePayload() {
    if (activePhotoReview?.issue_type !== FIELD_PHOTO_ISSUE_TYPE_VEHICLE) return {};
    return { vehicle_insurance_status: photoReviewVehicleInsuranceStatus() };
}

function updatePhotoReviewVehicleInsuranceUi() {
    const section = document.getElementById('photo-review-vehicle-insurance-section');
    const show = activePhotoReview?.issue_type === FIELD_PHOTO_ISSUE_TYPE_VEHICLE;
    if (section) section.hidden = !show;
    if (!show) return;
    const status = vehicleInsuranceStatus(activePhotoReview?.vehicle_insurance_status);
    photoReviewVehicleInsuranceInputs().forEach(input => {
        input.checked = input.value === status;
    });
    updatePhotoReviewVehicleInsuranceCheckedText();
}

function photoReviewVehicleInsuranceCheckedText() {
    const status = photoReviewVehicleInsuranceStatus();
    if (status === FIELD_PHOTO_VEHICLE_INSURANCE_STATUS_UNKNOWN) {
        return t('modal.photoReview.vehicleInsuranceCheckedUnknown');
    }
    const activeStatus = vehicleInsuranceStatus(activePhotoReview?.vehicle_insurance_status);
    const checkedAt = status === activeStatus ? humanDateTimeText(activePhotoReview?.vehicle_insurance_checked_at) : '';
    return checkedAt
        ? t('modal.photoReview.vehicleInsuranceCheckedAt', { date: checkedAt })
        : t('modal.photoReview.vehicleInsuranceCheckedPending');
}

function updatePhotoReviewVehicleInsuranceCheckedText() {
    const checkedText = document.getElementById('photo-review-vehicle-insurance-checked');
    if (checkedText) checkedText.textContent = photoReviewVehicleInsuranceCheckedText();
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
    button.disabled = !canDelete;
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
        return `
            <button type="button" class="photo-review-item ${active ? 'is-active' : ''}" onclick="selectPhotoReview('${escapeHtml(item.id)}')">
                <strong>${escapeHtml(display.title)}</strong>
                <span class="photo-review-pill">${escapeHtml(photoReviewStatusLabel(item.public_review_status))}</span>
                ${detailHtml}
            </button>
        `;
    }).join('');
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

async function loadPhotoReviewQueue() {
    if (photoReviewMode !== 'admin') return;
    if (!adminAuthenticated && !(await ensureAdmin())) return;
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
        if (data.status !== 'ok') {
            throw new Error(data.error || t('modal.photoReview.loadError'));
        }
        photoReviewItems = Array.isArray(data.photos) ? data.photos : [];
        activePhotoReview = null;
        photoReviewImage = null;
        photoReviewRedactions = [];
        activePhotoReviewRedactionIndex = -1;
        updatePhotoReviewDeleteAction();
        renderPhotoReviewQueue();
        clearPhotoReviewCanvas();
        if (photoReviewItems[0]) selectPhotoReview(photoReviewItems[0].id);
        setPhotoReviewStatusMessage();
    } catch (err) {
        setPhotoReviewStatusMessage(apiErrorMessage(err, t('modal.photoReview.loadError')));
    }
}

document.getElementById('photo-review-search')?.addEventListener('input', () => {
    photoReviewExactPhotoIds = [];
    if (photoReviewSearchTimer) clearTimeout(photoReviewSearchTimer);
    photoReviewSearchTimer = setTimeout(loadPhotoReviewQueue, 250);
});

photoReviewVehicleInsuranceInputs().forEach(input => {
    input.addEventListener('change', updatePhotoReviewVehicleInsuranceCheckedText);
});

document.getElementById('modal-photo-review')?.addEventListener('modalclose', () => {
    revokeOwnerPhotoReviewObjectUrl();
});

document.addEventListener('keydown', event => {
    if (event.key !== 'Escape' || !photoReviewRequiresSummaryReturn()) return;
    const confirmModal = document.getElementById('modal-confirm');
    const adminModal = document.getElementById('modal-admin-login');
    if ((confirmModal && !confirmModal.hidden) || (adminModal && !adminModal.hidden)) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    returnPhotoReviewToFieldPhotoSummary();
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
}

function revokeOwnerPhotoReviewObjectUrl() {
    if (!ownerPhotoReviewObjectUrl) return;
    URL.revokeObjectURL(ownerPhotoReviewObjectUrl);
    ownerPhotoReviewObjectUrl = null;
}

async function photoReviewOriginalImageSrc(item) {
    if (photoReviewMode !== 'owner') {
        return `${item.original_image}?ts=${Date.now()}`;
    }
    const resp = await fetch(item.original_image, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ edit_token: ownerPhotoReviewToken }),
    });
    if (!resp.ok) {
        const data = await resp.json().catch(() => ({}));
        throw new Error(data.error || t('modal.photoReview.imageError'));
    }
    const blob = await resp.blob();
    revokeOwnerPhotoReviewObjectUrl();
    ownerPhotoReviewObjectUrl = URL.createObjectURL(blob);
    return ownerPhotoReviewObjectUrl;
}

async function selectPhotoReview(itemId) {
    const item = photoReviewItems.find(candidate => candidate.id === itemId);
    if (!item) return;
    activePhotoReview = item;
    updatePhotoReviewVehicleInsuranceUi();
    photoReviewRedactions = (Array.isArray(item.redactions) ? item.redactions : [])
        .map(normalizePhotoReviewRedaction)
        .filter(Boolean);
    activePhotoReviewRedactionIndex = photoReviewRedactions.length ? photoReviewRedactions.length - 1 : -1;
    photoReviewDraftRect = null;
    updatePhotoReviewDeleteAction();
    renderPhotoReviewQueue();
    setPhotoReviewStatusMessage(t('modal.photoReview.imageLoading'));
    const image = new Image();
    image.onload = () => {
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
        photoReviewImage = null;
        clearPhotoReviewCanvas();
        setPhotoReviewStatusMessage(t('modal.photoReview.imageError'));
    };
    try {
        image.src = await photoReviewOriginalImageSrc(item);
    } catch (err) {
        photoReviewImage = null;
        clearPhotoReviewCanvas();
        setPhotoReviewStatusMessage(err.message || t('modal.photoReview.imageError'));
    }
}

async function savePhotoReviewStatus(publicReviewStatus) {
    const endpoint = photoReviewEndpoint(activePhotoReview);
    if (!endpoint) return;
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
            renderPhotoReviewQueue();
            updatePhotoReviewVehicleInsuranceUi();
            await loadFieldPhotos();
            return;
        }
        await loadFieldPhotos();
        await loadPhotoReviewQueue();
    } catch (err) {
        setPhotoReviewStatusMessage(apiErrorMessage(err, t('modal.photoReview.saveError')));
    }
}

async function deletePhotoReviewItem() {
    const endpoint = photoReviewDeleteEndpoint(activePhotoReview);
    if (!endpoint || activePhotoReview?.public_review_status !== 'rejected') return;
    const confirmed = await confirmAction({
        title: t('modal.photoReview.deleteTitle'),
        message: t('modal.photoReview.deleteConfirm'),
        confirmLabel: t('modal.photoReview.delete'),
    });
    if (!confirmed) return;
    setPhotoReviewStatusMessage(t('modal.photoReview.deleting'));
    try {
        const data = await apiDeleteJson(endpoint);
        if (data.status !== 'ok') {
            throw new Error(data.error || t('modal.photoReview.deleteError'));
        }
        setPhotoReviewStatusMessage(t('modal.photoReview.deleted'));
        await loadFieldPhotos();
        await loadPhotoReviewQueue();
    } catch (err) {
        setPhotoReviewStatusMessage(apiErrorMessage(err, t('modal.photoReview.deleteError')));
    }
}
