let lastFieldPhotoThanksToken = '';
let lastFieldPhotoThanksPhotoIds = [];

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

document.addEventListener('keydown', event => {
    if (event.key !== 'Escape' || !fieldPhotoThanksDraftRequiresDecision()) return;
    const confirmModal = document.getElementById('modal-confirm');
    const adminModal = document.getElementById('modal-admin-login');
    if ((confirmModal && !confirmModal.hidden) || (adminModal && !adminModal.hidden)) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    notifyFieldPhotoThanksDecisionRequired();
}, true);
