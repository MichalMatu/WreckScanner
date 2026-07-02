let fieldPhotoUploadItems = [];
let fieldPhotoUploadFallbackLatLng = null;
let fieldPhotoUploadEditToken = '';
let lastFieldPhotoThanksToken = '';
let lastFieldPhotoThanksPhotoIds = [];
let fieldPhotoLocationPickActive = false;
let fieldPhotoUploadInProgress = false;

function randomFieldPhotoEditToken() {
    const bytes = new Uint8Array(18);
    if (window.crypto?.getRandomValues) {
        window.crypto.getRandomValues(bytes);
    } else {
        bytes.forEach((_, index) => { bytes[index] = Math.floor(Math.random() * 256); });
    }
    let binary = '';
    bytes.forEach(byte => { binary += String.fromCharCode(byte); });
    return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '');
}

function ensureFieldPhotoUploadEditToken() {
    if (adminAuthenticated) return '';
    if (!fieldPhotoUploadEditToken) fieldPhotoUploadEditToken = randomFieldPhotoEditToken();
    return fieldPhotoUploadEditToken;
}

function openFieldPhotoThanksModal({
    saved = 0,
    editToken = '',
    photoIds = [],
    submitted = false,
    statusMessage = '',
} = {}) {
    const title = document.getElementById('field-photo-thanks-title');
    const count = document.getElementById('field-photo-thanks-count');
    const tokenSection = document.getElementById('field-photo-thanks-token-section');
    const tokenInput = document.getElementById('field-photo-thanks-token');
    const status = document.getElementById('field-photo-thanks-status');
    const reviewButton = document.getElementById('field-photo-thanks-review');
    const submitButton = document.getElementById('field-photo-thanks-submit');
    const discardButton = document.getElementById('field-photo-thanks-discard');
    const doneButton = document.getElementById('field-photo-thanks-done');
    const closeButton = document.getElementById('field-photo-thanks-close');
    const savedCount = Number(saved) || 0;
    const normalizedToken = String(editToken || '').trim();
    lastFieldPhotoThanksToken = normalizedToken;
    lastFieldPhotoThanksPhotoIds = Array.isArray(photoIds) ? photoIds.map(safeFieldPhotoId).filter(Boolean) : [];
    if (title) title.textContent = t(submitted ? 'modal.fieldPhotoThanks.title' : 'modal.fieldPhotoSummary.title');
    if (count) {
        count.textContent = t(
            submitted
                ? (savedCount === 1 ? 'modal.fieldPhotoThanks.summaryOne' : 'modal.fieldPhotoThanks.summaryMany')
                : (savedCount === 1 ? 'modal.fieldPhotoSummary.summaryOne' : 'modal.fieldPhotoSummary.summaryMany'),
            { n: savedCount }
        );
    }
    if (tokenSection) tokenSection.hidden = !normalizedToken;
    if (tokenInput) tokenInput.value = normalizedToken;
    if (reviewButton) reviewButton.hidden = !normalizedToken || !lastFieldPhotoThanksPhotoIds.length;
    if (submitButton) {
        submitButton.hidden = submitted || !normalizedToken || !lastFieldPhotoThanksPhotoIds.length;
        submitButton.disabled = false;
    }
    if (discardButton) {
        discardButton.hidden = submitted || !normalizedToken || !lastFieldPhotoThanksPhotoIds.length;
        discardButton.disabled = false;
    }
    if (doneButton) doneButton.hidden = !submitted;
    if (closeButton) closeButton.hidden = !submitted;
    if (status) status.textContent = statusMessage || '';
    openModal('modal-field-photo-thanks');
}

async function copyFieldPhotoThanksToken() {
    const token = lastFieldPhotoThanksToken || String(document.getElementById('field-photo-thanks-token')?.value || '');
    const status = document.getElementById('field-photo-thanks-status');
    if (!token.trim()) return;
    try {
        await navigator.clipboard.writeText(token.trim());
    } catch (_) {
        const input = document.getElementById('field-photo-thanks-token');
        input?.select();
        document.execCommand?.('copy');
    }
    if (status) status.textContent = t('modal.fieldPhotoThanks.copied');
}

async function submitFieldPhotoThanksForReview() {
    const status = document.getElementById('field-photo-thanks-status');
    const submitButton = document.getElementById('field-photo-thanks-submit');
    const token = String(lastFieldPhotoThanksToken || '').trim();
    const photoIds = lastFieldPhotoThanksPhotoIds.map(safeFieldPhotoId).filter(Boolean);
    const tokenError = validateFieldPhotoEditToken(token, { required: true });
    if (tokenError || !photoIds.length) {
        if (status) status.textContent = tokenError || t('modal.fieldPhotoSummary.submitError');
        return;
    }
    if (submitButton) submitButton.disabled = true;
    if (status) status.textContent = t('modal.fieldPhotoSummary.submitting');
    try {
        const data = await apiPostJson(`${FIELD_PHOTOS_URL}/owner-submit`, {
            photo_ids: photoIds,
            edit_token: token,
        });
        if (data.status !== 'ok') {
            throw new Error(data.error || t('modal.fieldPhotoSummary.submitError'));
        }
        const submittedIds = (Array.isArray(data.photos) ? data.photos : [])
            .map(photo => safeFieldPhotoId(photo.id))
            .filter(Boolean);
        await loadFieldPhotos();
        openFieldPhotoThanksModal({
            saved: submittedIds.length || photoIds.length,
            editToken: token,
            photoIds: submittedIds.length ? submittedIds : photoIds,
            submitted: true,
        });
    } catch (err) {
        if (status) status.textContent = apiErrorMessage(err, t('modal.fieldPhotoSummary.submitError'));
        if (submitButton) submitButton.disabled = false;
    }
}

function clearFieldPhotoThanksDraftState() {
    lastFieldPhotoThanksToken = '';
    lastFieldPhotoThanksPhotoIds = [];
    fieldPhotoUploadEditToken = '';
}

function fieldPhotoUploadSavedDraftPhotoIds() {
    if (adminAuthenticated) return [];
    return fieldPhotoUploadItems
        .filter(item => item.status === 'saved')
        .map(item => safeFieldPhotoId(item.photo?.id))
        .filter(Boolean);
}

function fieldPhotoUploadSavedDraftToken() {
    if (adminAuthenticated) return '';
    return String(
        fieldPhotoUploadEditToken
        || fieldPhotoUploadItems.find(item => item.status === 'saved' && item.editToken)?.editToken
        || ''
    ).trim();
}

function openFieldPhotoUploadSavedDraftSummary(statusMessage = '') {
    const photoIds = fieldPhotoUploadSavedDraftPhotoIds();
    const editToken = fieldPhotoUploadSavedDraftToken();
    if (!photoIds.length || !editToken) return false;
    openFieldPhotoThanksModal({
        saved: photoIds.length,
        editToken,
        photoIds,
        submitted: false,
        statusMessage,
    });
    return true;
}

function notifyFieldPhotoUploadBusy() {
    const status = document.getElementById('field-photo-status');
    if (status) status.textContent = t('modal.fieldPhoto.uploadInProgress');
}

function closeFieldPhotoUploadModal(target) {
    if (fieldPhotoUploadInProgress) {
        notifyFieldPhotoUploadBusy();
        return;
    }
    if (openFieldPhotoUploadSavedDraftSummary(t('modal.fieldPhotoSummary.closeUploadWithDrafts'))) return;
    closeModal(target instanceof Element ? target : document.getElementById('modal-field-photo-upload'));
}

function fieldPhotoThanksDraftRequiresDecision() {
    const modal = document.getElementById('modal-field-photo-thanks');
    const submitButton = document.getElementById('field-photo-thanks-submit');
    return Boolean(
        modal
        && !modal.hidden
        && submitButton
        && !submitButton.hidden
        && lastFieldPhotoThanksToken
        && lastFieldPhotoThanksPhotoIds.length
    );
}

function notifyFieldPhotoThanksDecisionRequired() {
    const status = document.getElementById('field-photo-thanks-status');
    if (status) status.textContent = t('modal.fieldPhotoSummary.closeBlocked');
}

function closeFieldPhotoThanksModal(target) {
    if (fieldPhotoThanksDraftRequiresDecision()) {
        notifyFieldPhotoThanksDecisionRequired();
        return;
    }
    closeModal(target instanceof Element ? target : document.getElementById('modal-field-photo-thanks'));
}

async function discardFieldPhotoThanksDraft() {
    const status = document.getElementById('field-photo-thanks-status');
    const discardButton = document.getElementById('field-photo-thanks-discard');
    const token = String(lastFieldPhotoThanksToken || '').trim();
    const photoIds = lastFieldPhotoThanksPhotoIds.map(safeFieldPhotoId).filter(Boolean);
    const tokenError = validateFieldPhotoEditToken(token, { required: true });
    if (tokenError || !photoIds.length) {
        if (status) status.textContent = tokenError || t('modal.fieldPhotoSummary.discardError');
        return;
    }
    const confirmed = await confirmAction({
        title: t('modal.fieldPhotoSummary.discardTitle'),
        message: t('modal.fieldPhotoSummary.discardConfirm', { n: photoIds.length }),
        confirmLabel: t('modal.fieldPhotoSummary.discard'),
    });
    if (!confirmed) return;

    if (discardButton) discardButton.disabled = true;
    if (status) status.textContent = t('modal.fieldPhotoSummary.discarding');
    try {
        const data = await apiPostJson(`${FIELD_PHOTOS_URL}/owner-discard`, {
            photo_ids: photoIds,
            edit_token: token,
        });
        if (data.status !== 'ok') {
            throw new Error(data.error || t('modal.fieldPhotoSummary.discardError'));
        }
        clearFieldPhotoThanksDraftState();
        await loadFieldPhotos();
        closeModal(document.getElementById('modal-field-photo-thanks'));
        statusEl.textContent = t('modal.fieldPhotoSummary.discarded');
        statusEl.className = 'ok';
    } catch (err) {
        if (status) status.textContent = apiErrorMessage(err, t('modal.fieldPhotoSummary.discardError'));
        if (discardButton) discardButton.disabled = false;
    }
}

async function openFieldPhotoThanksOwnerReview() {
    const status = document.getElementById('field-photo-thanks-status');
    const token = String(lastFieldPhotoThanksToken || '').trim();
    const photoIds = lastFieldPhotoThanksPhotoIds.map(safeFieldPhotoId).filter(Boolean);
    const tokenError = validateFieldPhotoEditToken(token, { required: true });
    if (tokenError || !photoIds.length || typeof openFieldPhotoOwnerReviewWithToken !== 'function') {
        if (status) status.textContent = tokenError || t('modal.fieldPhotoOwner.unlockError');
        return;
    }
    if (status) status.textContent = t('modal.fieldPhotoOwner.loading');
    try {
        await openFieldPhotoOwnerReviewWithToken(photoIds, token, {
            sourceModalId: 'modal-field-photo-thanks',
            returnToFieldPhotoSummary: true,
        });
    } catch (err) {
        if (status) status.textContent = apiErrorMessage(err, t('modal.fieldPhotoOwner.unlockError'));
    }
}

function validateFieldPhotoEditToken(token, options = {}) {
    const normalized = String(token || '').trim();
    const required = options.required ?? !adminAuthenticated;
    if (!required) return '';
    if (normalized.length < FIELD_PHOTO_EDIT_TOKEN_MIN_LENGTH) return t('modal.fieldPhoto.editTokenRequired');
    if (normalized.length > FIELD_PHOTO_EDIT_TOKEN_MAX_LENGTH) return t('modal.fieldPhoto.editTokenTooLong');
    return '';
}

function updateFieldPhotoFallbackText() {
    const el = document.getElementById('field-photo-fallback');
    if (!el) return;
    const point = fieldPhotoUploadFallbackLatLng || (typeof map !== 'undefined' ? map.getCenter() : null);
    if (!point) return;
    el.textContent = t('modal.fieldPhoto.fallbackCoords', {
        lat: Number(point.lat).toFixed(6),
        lon: Number(point.lng).toFixed(6),
    });
}

function currentFieldPhotoUploadFallbackLatLng() {
    return fieldPhotoUploadFallbackLatLng || map.getCenter();
}

function updatePanelFieldPhotoLocationPickUi() {
    const button = document.getElementById('panel-add-field-photo');
    if (button) {
        button.classList.toggle('is-picking-location', fieldPhotoLocationPickActive);
        button.setAttribute('aria-pressed', fieldPhotoLocationPickActive ? 'true' : 'false');
        button.title = t(fieldPhotoLocationPickActive ? 'panel.addPhotoPickingTitle' : 'panel.addPhotoTitle');
        const label = button.querySelector('[data-panel-add-photo-label]');
        if (label) label.textContent = t(fieldPhotoLocationPickActive ? 'panel.addPhotoPicking' : 'panel.addPhoto');
    }
    map?.getContainer()?.classList.toggle('is-picking-field-photo-location', fieldPhotoLocationPickActive);
    if (fieldPhotoLocationPickActive) {
        statusEl.textContent = t('panel.addPhotoPickStatus');
        statusEl.className = 'ok';
    }
}

function cancelFieldPhotoLocationPick(options = {}) {
    if (!fieldPhotoLocationPickActive) return;
    fieldPhotoLocationPickActive = false;
    map.off('click', handlePanelFieldPhotoLocationPick);
    updatePanelFieldPhotoLocationPickUi();
    if (options.clearStatus && statusEl.textContent === t('panel.addPhotoPickStatus')) {
        statusEl.textContent = '';
        statusEl.className = '';
    }
}

function startFieldPhotoLocationPick() {
    if (!publicFeatureAllowed(PUBLIC_FEATURE_KEYS.photoUploads) || !fieldPhotoAnyIssueAllowed()) return;
    if (fieldPhotoLocationPickActive) {
        cancelFieldPhotoLocationPick({ clearStatus: true });
        return;
    }
    closeMapContextMenu?.();
    fieldPhotoLocationPickActive = true;
    map.on('click', handlePanelFieldPhotoLocationPick);
    updatePanelFieldPhotoLocationPickUi();
    statusEl.textContent = t('panel.addPhotoPickStatus');
    statusEl.className = 'ok';
}

function isFieldPhotoLocationPickActive() {
    return fieldPhotoLocationPickActive;
}

async function handlePanelFieldPhotoLocationPick(e) {
    if (!fieldPhotoLocationPickActive) return;
    const fallbackLatLng = L.latLng(e.latlng.lat, e.latlng.lng);
    cancelFieldPhotoLocationPick({ clearStatus: true });
    await openFieldPhotoUploadModal({
        fallbackLatLng,
        ignoreExifGps: true,
        issueType: FIELD_PHOTO_ISSUE_TYPE_VEHICLE,
    });
}

function resetFieldPhotoUploadModal(options = {}) {
    const form = document.getElementById('field-photo-form');
    const status = document.getElementById('field-photo-status');
    const submit = document.getElementById('field-photo-submit');
    const queue = document.getElementById('field-photo-queue');
    const retry = document.getElementById('field-photo-retry');
    const ignoreExif = document.getElementById('field-photo-ignore-exif');
    const filesInput = document.getElementById('field-photo-files');
    const issueSelect = document.getElementById('field-photo-issue-type');
    fieldPhotoUploadItems = [];
    fieldPhotoUploadEditToken = '';
    form?.reset();
    updateFilePickerSummary(filesInput);
    const rawFallback = options.fallbackLatLng;
    fieldPhotoUploadFallbackLatLng = rawFallback && Number.isFinite(Number(rawFallback.lat)) && Number.isFinite(Number(rawFallback.lng))
        ? L.latLng(Number(rawFallback.lat), Number(rawFallback.lng))
        : (typeof map !== 'undefined' ? map.getCenter() : null);
    const requestedIssueType = FIELD_PHOTO_ISSUE_TYPES.has(options.issueType)
        ? options.issueType
        : FIELD_PHOTO_ISSUE_TYPE_VEHICLE;
    if (issueSelect) issueSelect.value = requestedIssueType;
    updateFieldPhotoIssueOptions();
    if (ignoreExif) ignoreExif.checked = Boolean(options.ignoreExifGps);
    updateFieldPhotoFallbackText();
    if (status) status.textContent = '';
    if (queue) {
        queue.hidden = true;
        queue.innerHTML = '';
    }
    if (retry) {
        retry.hidden = true;
        retry.disabled = false;
    }
    if (submit) {
        submit.disabled = false;
        submit.querySelector('span').textContent = t('modal.fieldPhoto.submit');
    }
    fieldPhotoUploadInProgress = false;
}

async function openFieldPhotoUploadModal(options = {}) {
    if (!publicFeatureAllowed(PUBLIC_FEATURE_KEYS.photoUploads) || !fieldPhotoAnyIssueAllowed()) return;
    resetFieldPhotoUploadModal(options);
    openModal('modal-field-photo-upload');
}

async function openFieldPhotoUploadFromPanel() {
    startFieldPhotoLocationPick();
}

async function openFieldPhotoUploadAtContextPoint() {
    if (
        !publicFeatureAllowed(PUBLIC_FEATURE_KEYS.photoUploads)
        || !fieldPhotoAnyIssueAllowed()
        || !contextMenuLatLng
    ) return;
    const fallbackLatLng = L.latLng(contextMenuLatLng.lat, contextMenuLatLng.lng);
    closeMapContextMenu();
    await openFieldPhotoUploadModal({
        fallbackLatLng,
        ignoreExifGps: true,
        issueType: FIELD_PHOTO_ISSUE_TYPE_VEHICLE,
    });
}

function fieldPhotoFileSizeLabel(bytes) {
    const size = Number(bytes) || 0;
    if (size >= 1024 * 1024) return `${(size / (1024 * 1024)).toFixed(1)} MB`;
    if (size >= 1024) return `${Math.ceil(size / 1024)} KB`;
    return `${size} B`;
}

function fieldPhotoValidationError(file) {
    if (file.size > FIELD_PHOTO_MAX_BYTES) {
        return t('modal.fieldPhoto.fileLimitError');
    }
    if (file.type && !FIELD_PHOTO_ALLOWED_TYPES.has(file.type)) {
        return t('modal.fieldPhoto.fileTypeError');
    }
    return '';
}

function validateFieldPhotoFiles(files) {
    const photoFiles = Array.from(files || []);
    if (!photoFiles.length) {
        throw new Error(t('modal.fieldPhoto.noFiles'));
    }
    if (photoFiles.length > FIELD_PHOTO_MAX_FILES) {
        throw new Error(t('modal.fieldPhoto.fileCountError', { n: FIELD_PHOTO_MAX_FILES }));
    }
    return photoFiles.map((file, index) => {
        const error = fieldPhotoValidationError(file);
        return {
            file,
            index,
            status: error ? 'error' : 'pending',
            message: error,
            validationError: Boolean(error),
            fallbackLat: null,
            fallbackLon: null,
            ignoreExifGps: false,
        };
    });
}

function fieldPhotoQueueStatusLabel(item) {
    if (item.status === 'saved') {
        return adminAuthenticated ? t('modal.fieldPhoto.queueSaved') : t('modal.fieldPhoto.queuePrepared');
    }
    if (item.status === 'uploading') return t('modal.fieldPhoto.queueUploading');
    if (item.status === 'error') return item.message || t('fieldPhoto.saveError');
    return t('modal.fieldPhoto.queuePending');
}

function updateFieldPhotoRetryButton(uploading = false) {
    const retry = document.getElementById('field-photo-retry');
    if (!retry) return;
    const hasRetryable = fieldPhotoUploadItems.some(item => item.status === 'error' && !item.validationError);
    retry.hidden = !hasRetryable;
    retry.disabled = uploading;
}

function renderFieldPhotoQueue(uploading = false) {
    const queue = document.getElementById('field-photo-queue');
    if (!queue) return;
    if (!fieldPhotoUploadItems.length) {
        queue.hidden = true;
        queue.innerHTML = '';
        updateFieldPhotoRetryButton(uploading);
        return;
    }
    queue.hidden = false;
    queue.innerHTML = fieldPhotoUploadItems.map(item => `
        <div class="field-photo-queue-item field-photo-queue-item--${item.status}">
            <span class="field-photo-queue-name">${escapeHtml(item.file.name || '-')}</span>
            <span class="field-photo-queue-size">${escapeHtml(fieldPhotoFileSizeLabel(item.file.size))}</span>
            <span class="field-photo-queue-status">${escapeHtml(fieldPhotoQueueStatusLabel(item))}</span>
        </div>
    `).join('');
    updateFieldPhotoRetryButton(uploading);
}

function fieldPhotoUploadSummary() {
    const saved = fieldPhotoUploadItems.filter(item => item.status === 'saved').length;
    const failed = fieldPhotoUploadItems.filter(item => item.status === 'error').length;
    return { saved, failed, total: fieldPhotoUploadItems.length };
}

async function uploadFieldPhotoItems(items) {
    const input = document.getElementById('field-photo-files');
    const status = document.getElementById('field-photo-status');
    const submit = document.getElementById('field-photo-submit');
    const submittedEditToken = adminAuthenticated
        ? ''
        : (fieldPhotoUploadEditToken || items.find(item => item.editToken)?.editToken || ensureFieldPhotoUploadEditToken());
    if (submit) {
        submit.disabled = true;
        submit.querySelector('span').textContent = t('modal.fieldPhoto.uploading');
    }
    fieldPhotoUploadInProgress = true;
    try {
        updateFieldPhotoRetryButton(true);

        let attempted = 0;
        for (const item of items) {
            item.status = 'uploading';
            item.message = '';
            renderFieldPhotoQueue(true);
            if (status) status.textContent = t('modal.fieldPhoto.uploadProgress', { done: attempted + 1, total: items.length });
            const formData = new FormData();
            formData.append('fallback_lat', item.fallbackLat);
            formData.append('fallback_lon', item.fallbackLon);
            formData.append('ignore_exif_gps', item.ignoreExifGps ? '1' : '0');
            formData.append('issue_type', item.issueType || FIELD_PHOTO_ISSUE_TYPE_VEHICLE);
            item.editToken = item.editToken || submittedEditToken;
            if (item.editToken) formData.append('edit_token', item.editToken);
            formData.append('photo', item.file);
            try {
                const data = await apiJson(FIELD_PHOTOS_URL, { method: 'POST', body: formData });
                if (data.status !== 'ok') {
                    throw new Error(data.error || t('fieldPhoto.saveError'));
                }
                item.status = 'saved';
                item.photo = data.photo || null;
                item.message = '';
            } catch (err) {
                item.status = 'error';
                item.validationError = false;
                item.message = err.message || t('fieldPhoto.saveError');
            }
            attempted += 1;
            renderFieldPhotoQueue(true);
        }

        await loadFieldPhotos();
        const summary = fieldPhotoUploadSummary();
        if (status) {
            status.textContent = summary.failed
                ? t('modal.fieldPhoto.uploadSummaryWithErrors', summary)
                : adminAuthenticated
                    ? t('modal.fieldPhoto.saved', { n: summary.saved })
                    : t('modal.fieldPhoto.prepared', { n: summary.saved });
        }
        const savedPhotoIds = fieldPhotoUploadSavedDraftPhotoIds();
        if (!adminAuthenticated && savedPhotoIds.length) {
            const partialMessage = summary.failed ? t('modal.fieldPhotoSummary.partialUpload') : '';
            if (input) {
                input.value = '';
                updateFilePickerSummary(input);
            }
            openFieldPhotoThanksModal({
                saved: savedPhotoIds.length,
                editToken: submittedEditToken,
                photoIds: savedPhotoIds,
                submitted: false,
                statusMessage: partialMessage,
            });
        } else if (!summary.failed) {
            if (input) {
                input.value = '';
                updateFilePickerSummary(input);
            }
            if (adminAuthenticated) {
                closeModal(document.getElementById('modal-field-photo-upload'));
            }
        }
    } finally {
        if (submit) {
            submit.disabled = false;
            submit.querySelector('span').textContent = t('modal.fieldPhoto.submit');
        }
        fieldPhotoUploadInProgress = false;
        renderFieldPhotoQueue(false);
    }
}

async function submitFieldPhotoUpload(event) {
    event.preventDefault();
    if (!publicFeatureAllowed(PUBLIC_FEATURE_KEYS.photoUploads)) return;
    const input = document.getElementById('field-photo-files');
    const status = document.getElementById('field-photo-status');
    try {
        fieldPhotoUploadItems = validateFieldPhotoFiles(input?.files);
    } catch (err) {
        fieldPhotoUploadItems = [];
        renderFieldPhotoQueue();
        if (status) status.textContent = err.message;
        return;
    }
    const validationErrors = fieldPhotoUploadItems.filter(item => item.validationError);
    if (validationErrors.length) {
        renderFieldPhotoQueue();
        if (status) {
            status.textContent = validationErrors.length === 1
                ? validationErrors[0].message
                : t('modal.fieldPhoto.validationErrorHint');
        }
        return;
    }

    const fallbackLatLng = currentFieldPhotoUploadFallbackLatLng();
    const ignoreExifGps = document.getElementById('field-photo-ignore-exif')?.checked === true;
    const selectedIssueType = document.getElementById('field-photo-issue-type')?.value || FIELD_PHOTO_ISSUE_TYPE_VEHICLE;
    const issueType = FIELD_PHOTO_ISSUE_TYPES.has(selectedIssueType) ? selectedIssueType : FIELD_PHOTO_ISSUE_TYPE_VEHICLE;
    const editToken = ensureFieldPhotoUploadEditToken();
    const tokenError = validateFieldPhotoEditToken(editToken);
    if (tokenError) {
        if (status) status.textContent = tokenError;
        return;
    }
    if (!fieldPhotoIssueAllowed(issueType)) {
        if (status) status.textContent = t('modal.fieldPhoto.issueTypeUnavailable');
        return;
    }
    fieldPhotoUploadItems.forEach(item => {
        item.fallbackLat = fallbackLatLng.lat;
        item.fallbackLon = fallbackLatLng.lng;
        item.ignoreExifGps = ignoreExifGps;
        item.issueType = issueType;
        item.editToken = adminAuthenticated ? '' : editToken;
    });
    renderFieldPhotoQueue();
    const uploadable = fieldPhotoUploadItems.filter(item => item.status === 'pending');
    if (!uploadable.length) {
        if (status) status.textContent = t('modal.fieldPhoto.noValidFiles');
        return;
    }
    await uploadFieldPhotoItems(uploadable);
}

async function retryFailedFieldPhotoUploads() {
    if (!publicFeatureAllowed(PUBLIC_FEATURE_KEYS.photoUploads)) return;
    const fallbackLatLng = currentFieldPhotoUploadFallbackLatLng();
    const editToken = ensureFieldPhotoUploadEditToken();
    const retryable = fieldPhotoUploadItems.filter(item => item.status === 'error' && !item.validationError);
    retryable.forEach(item => {
        item.status = 'pending';
        item.message = '';
        item.fallbackLat = item.fallbackLat ?? fallbackLatLng.lat;
        item.fallbackLon = item.fallbackLon ?? fallbackLatLng.lng;
        item.ignoreExifGps = Boolean(item.ignoreExifGps);
        item.issueType = item.issueType || FIELD_PHOTO_ISSUE_TYPE_VEHICLE;
        item.editToken = item.editToken || (adminAuthenticated ? '' : editToken);
    });
    renderFieldPhotoQueue();
    if (!retryable.length) {
        const status = document.getElementById('field-photo-status');
        if (status) status.textContent = t('modal.fieldPhoto.noRetryableFiles');
        return;
    }
    await uploadFieldPhotoItems(retryable);
}

document.addEventListener('keydown', event => {
    if (event.key === 'Escape') cancelFieldPhotoLocationPick({ clearStatus: true });
});
document.addEventListener('keydown', event => {
    const uploadModal = document.getElementById('modal-field-photo-upload');
    if (event.key !== 'Escape' || !uploadModal || uploadModal.hidden) return;
    const confirmModal = document.getElementById('modal-confirm');
    const adminModal = document.getElementById('modal-admin-login');
    if ((confirmModal && !confirmModal.hidden) || (adminModal && !adminModal.hidden)) return;
    if (fieldPhotoUploadInProgress) {
        event.preventDefault();
        event.stopImmediatePropagation();
        notifyFieldPhotoUploadBusy();
        return;
    }
    if (!fieldPhotoUploadSavedDraftPhotoIds().length) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    openFieldPhotoUploadSavedDraftSummary(t('modal.fieldPhotoSummary.closeUploadWithDrafts'));
}, true);
document.addEventListener('keydown', event => {
    if (event.key !== 'Escape' || !fieldPhotoThanksDraftRequiresDecision()) return;
    const confirmModal = document.getElementById('modal-confirm');
    const adminModal = document.getElementById('modal-admin-login');
    if ((confirmModal && !confirmModal.hidden) || (adminModal && !adminModal.hidden)) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    notifyFieldPhotoThanksDecisionRequired();
}, true);
document.addEventListener('langchange', updatePanelFieldPhotoLocationPickUi);
