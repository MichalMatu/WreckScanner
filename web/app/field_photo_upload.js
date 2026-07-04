let fieldPhotoUploadItems = [];
let fieldPhotoUploadMapLatLng = null;
let fieldPhotoUploadEditToken = '';
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

function validateFieldPhotoEditToken(token, options = {}) {
    const normalized = String(token || '').trim();
    const required = options.required ?? !adminAuthenticated;
    if (!required) return '';
    if (normalized.length < FIELD_PHOTO_EDIT_TOKEN_MIN_LENGTH) return t('modal.fieldPhoto.editTokenRequired');
    if (normalized.length > FIELD_PHOTO_EDIT_TOKEN_MAX_LENGTH) return t('modal.fieldPhoto.editTokenTooLong');
    return '';
}

function updateFieldPhotoMapPointText() {
    const el = document.getElementById('field-photo-map-point');
    if (!el) return;
    const point = fieldPhotoUploadMapLatLng || (typeof map !== 'undefined' ? map.getCenter() : null);
    if (!point) return;
    el.textContent = t('modal.fieldPhoto.mapPointCoords', {
        lat: Number(point.lat).toFixed(6),
        lon: Number(point.lng).toFixed(6),
    });
}

function currentFieldPhotoUploadMapLatLng() {
    return fieldPhotoUploadMapLatLng || map.getCenter();
}

function updateFieldPhotoLocationPickHintUi() {
    const hint = document.getElementById('map-field-photo-pick-hint');
    if (!hint) return;
    hint.hidden = !fieldPhotoLocationPickActive;
    const label = hint.querySelector('[data-map-pick-hint-label]');
    if (label) label.textContent = t('panel.addPhotoPickStatus');
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
    updateFieldPhotoLocationPickHintUi();
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
    if (typeof closeAppMenu === 'function') closeAppMenu();
    fieldPhotoLocationPickActive = true;
    map.on('click', handlePanelFieldPhotoLocationPick);
    updatePanelFieldPhotoLocationPickUi();
}

function isFieldPhotoLocationPickActive() {
    return fieldPhotoLocationPickActive;
}

async function handlePanelFieldPhotoLocationPick(e) {
    if (!fieldPhotoLocationPickActive) return;
    const mapLatLng = L.latLng(e.latlng.lat, e.latlng.lng);
    cancelFieldPhotoLocationPick({ clearStatus: true });
    await openFieldPhotoUploadModal({
        mapLatLng,
        issueType: FIELD_PHOTO_ISSUE_TYPE_VEHICLE,
    });
}

function resetFieldPhotoUploadModal(options = {}) {
    const form = document.getElementById('field-photo-form');
    const status = document.getElementById('field-photo-status');
    const submit = document.getElementById('field-photo-submit');
    const queue = document.getElementById('field-photo-queue');
    const retry = document.getElementById('field-photo-retry');
    const filesInput = document.getElementById('field-photo-files');
    const issueSelect = document.getElementById('field-photo-issue-type');
    fieldPhotoUploadItems = [];
    fieldPhotoUploadEditToken = '';
    form?.reset();
    updateFilePickerSummary(filesInput);
    const rawMapPoint = options.mapLatLng;
    fieldPhotoUploadMapLatLng = rawMapPoint && Number.isFinite(Number(rawMapPoint.lat)) && Number.isFinite(Number(rawMapPoint.lng))
        ? L.latLng(Number(rawMapPoint.lat), Number(rawMapPoint.lng))
        : (typeof map !== 'undefined' ? map.getCenter() : null);
    const requestedIssueType = FIELD_PHOTO_ISSUE_TYPES.has(options.issueType)
        ? options.issueType
        : FIELD_PHOTO_ISSUE_TYPE_VEHICLE;
    if (issueSelect) issueSelect.value = requestedIssueType;
    updateFieldPhotoIssueOptions();
    updateFieldPhotoMapPointText();
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
    const mapLatLng = L.latLng(contextMenuLatLng.lat, contextMenuLatLng.lng);
    closeMapContextMenu();
    await openFieldPhotoUploadModal({
        mapLatLng,
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
            mapLat: null,
            mapLon: null,
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

function fieldPhotoSubmittedEditToken(items) {
    if (adminAuthenticated) return '';
    return fieldPhotoUploadEditToken
        || items.find(item => item.editToken)?.editToken
        || ensureFieldPhotoUploadEditToken();
}

function setFieldPhotoUploadSubmitState(uploading) {
    const submit = document.getElementById('field-photo-submit');
    if (!submit) return;
    submit.disabled = uploading;
    submit.querySelector('span').textContent = t(uploading ? 'modal.fieldPhoto.uploading' : 'modal.fieldPhoto.submit');
}

function resetFieldPhotoFileInput(input) {
    if (!input) return;
    input.value = '';
    updateFilePickerSummary(input);
}

function fieldPhotoUploadResultText(summary) {
    if (summary.failed) return t('modal.fieldPhoto.uploadSummaryWithErrors', summary);
    return adminAuthenticated
        ? t('modal.fieldPhoto.saved', { n: summary.saved })
        : t('modal.fieldPhoto.prepared', { n: summary.saved });
}

function fieldPhotoUploadFormData(item, submittedEditToken) {
    const formData = new FormData();
    formData.append('map_lat', item.mapLat);
    formData.append('map_lon', item.mapLon);
    formData.append('issue_type', item.issueType || FIELD_PHOTO_ISSUE_TYPE_VEHICLE);
    item.editToken = item.editToken || submittedEditToken;
    if (item.editToken) formData.append('edit_token', item.editToken);
    formData.append('photo', item.file);
    return formData;
}

async function uploadSingleFieldPhotoItem(item, submittedEditToken) {
    try {
        const data = await apiJson(FIELD_PHOTOS_URL, {
            method: 'POST',
            body: fieldPhotoUploadFormData(item, submittedEditToken),
        });
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
}

function completeFieldPhotoUpload(input, summary, submittedEditToken) {
    const savedPhotoIds = fieldPhotoUploadSavedDraftPhotoIds();
    if (!adminAuthenticated && savedPhotoIds.length) {
        resetFieldPhotoFileInput(input);
        openFieldPhotoThanksModal({
            saved: savedPhotoIds.length,
            editToken: submittedEditToken,
            photoIds: savedPhotoIds,
            submitted: false,
            statusMessage: summary.failed ? t('modal.fieldPhotoSummary.partialUpload') : '',
        });
        return;
    }
    if (summary.failed) return;
    resetFieldPhotoFileInput(input);
    if (adminAuthenticated) {
        closeModal(document.getElementById('modal-field-photo-upload'));
    }
}

async function uploadFieldPhotoItems(items) {
    const input = document.getElementById('field-photo-files');
    const status = document.getElementById('field-photo-status');
    const submittedEditToken = fieldPhotoSubmittedEditToken(items);
    setFieldPhotoUploadSubmitState(true);
    fieldPhotoUploadInProgress = true;
    try {
        updateFieldPhotoRetryButton(true);

        let attempted = 0;
        for (const item of items) {
            item.status = 'uploading';
            item.message = '';
            renderFieldPhotoQueue(true);
            if (status) status.textContent = t('modal.fieldPhoto.uploadProgress', { done: attempted + 1, total: items.length });
            await uploadSingleFieldPhotoItem(item, submittedEditToken);
            attempted += 1;
            renderFieldPhotoQueue(true);
        }

        await loadFieldPhotos();
        const summary = fieldPhotoUploadSummary();
        if (status) status.textContent = fieldPhotoUploadResultText(summary);
        completeFieldPhotoUpload(input, summary, submittedEditToken);
    } finally {
        setFieldPhotoUploadSubmitState(false);
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

    const mapLatLng = currentFieldPhotoUploadMapLatLng();
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
        item.mapLat = mapLatLng.lat;
        item.mapLon = mapLatLng.lng;
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
    const mapLatLng = currentFieldPhotoUploadMapLatLng();
    const editToken = ensureFieldPhotoUploadEditToken();
    const retryable = fieldPhotoUploadItems.filter(item => item.status === 'error' && !item.validationError);
    retryable.forEach(item => {
        item.status = 'pending';
        item.message = '';
        item.mapLat = item.mapLat ?? mapLatLng.lat;
        item.mapLon = item.mapLon ?? mapLatLng.lng;
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
document.addEventListener('langchange', updatePanelFieldPhotoLocationPickUi);
