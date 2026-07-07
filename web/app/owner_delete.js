const OWNER_DELETABLE_PHOTO_STATUSES = new Set(['draft', 'pending']);
let fieldPhotoThanksSubmittedCanDelete = false;

function ownerPhotoReviewCanDelete(item = activePhotoReview) {
    return photoReviewMode === 'owner'
        && OWNER_DELETABLE_PHOTO_STATUSES.has(String(item?.public_review_status || '').trim());
}

function showOwnerPhotoReviewDeleteButton() {
    const button = document.getElementById('photo-review-delete');
    if (!button) return;
    button.hidden = false;
    button.disabled = photoReviewActionInFlight || !ownerPhotoReviewCanDelete();
}

const originalUpdatePhotoReviewDeleteAction = updatePhotoReviewDeleteAction;
updatePhotoReviewDeleteAction = function updatePhotoReviewDeleteAction() {
    if (ownerPhotoReviewCanDelete()) {
        showOwnerPhotoReviewDeleteButton();
        return;
    }
    originalUpdatePhotoReviewDeleteAction();
};

const originalSetPhotoReviewMode = setPhotoReviewMode;
setPhotoReviewMode = function setPhotoReviewMode(mode = 'admin') {
    originalSetPhotoReviewMode(mode);
    updatePhotoReviewDeleteAction();
};

async function deleteOwnerPhotoReviewItem() {
    if (photoReviewActionInFlight || !ownerPhotoReviewCanDelete()) return;
    const deletedPhotoId = safeFieldPhotoId(activePhotoReview?.photo_id);
    if (!deletedPhotoId) return;
    const deletedPhotoIndex = photoReviewActiveIndex(activePhotoReview.id);
    const confirmed = await confirmAction({
        title: t('modal.photoReview.deleteTitle'),
        message: t('modal.photoReview.deleteConfirm'),
        confirmLabel: t('modal.photoReview.delete'),
    });
    if (!confirmed) return;

    setPhotoReviewActionInFlight(true);
    setPhotoReviewStatusMessage(t('modal.photoReview.deleting'));
    try {
        const data = await apiPostJson(`${FIELD_PHOTOS_URL}/owner-delete`, {
            photo_ids: [deletedPhotoId],
            edit_token: ownerPhotoReviewToken,
        });
        if (data.status !== 'ok') {
            throw new Error(data.error || t('modal.photoReview.deleteError'));
        }

        photoReviewItems = photoReviewItems.filter(item => safeFieldPhotoId(item.photo_id) !== deletedPhotoId);
        ownerFieldPhotoIds = ownerFieldPhotoIds.filter(id => safeFieldPhotoId(id) !== deletedPhotoId);
        lastFieldPhotoThanksPhotoIds = lastFieldPhotoThanksPhotoIds.filter(id => safeFieldPhotoId(id) !== deletedPhotoId);
        await loadFieldPhotos();

        if (!photoReviewItems.length) {
            activePhotoReview = null;
            photoReviewImage = null;
            photoReviewRedactions = [];
            activePhotoReviewRedactionIndex = -1;
            photoReviewDraftRect = null;
            renderPhotoReviewQueue();
            clearPhotoReviewCanvas();
            setPhotoReviewStatusMessage(t('modal.photoReview.deleted'));
            return;
        }

        const nextItem = photoReviewItems[Math.min(deletedPhotoIndex, photoReviewItems.length - 1)];
        renderPhotoReviewQueue();
        clearPhotoReviewCanvas();
        setPhotoReviewStatusMessage(t('modal.photoReview.deleted'));
        if (nextItem) selectPhotoReview(nextItem.id);
    } catch (err) {
        setPhotoReviewStatusMessage(apiErrorMessage(err, t('modal.photoReview.deleteError')));
    } finally {
        setPhotoReviewActionInFlight(false);
    }
}

const originalDeletePhotoReviewItem = deletePhotoReviewItem;
deletePhotoReviewItem = async function deletePhotoReviewItem() {
    if (ownerPhotoReviewCanDelete()) {
        await deleteOwnerPhotoReviewItem();
        return;
    }
    await originalDeletePhotoReviewItem();
};

const originalOpenFieldPhotoThanksModal = openFieldPhotoThanksModal;
openFieldPhotoThanksModal = function openFieldPhotoThanksModal(options = {}) {
    fieldPhotoThanksSubmittedCanDelete = Boolean(options.submitted);
    originalOpenFieldPhotoThanksModal(options);
    const discardButton = document.getElementById('field-photo-thanks-discard');
    if (!discardButton || !fieldPhotoThanksSubmittedCanDelete) return;
    if (!lastFieldPhotoThanksToken || !lastFieldPhotoThanksPhotoIds.length) return;
    discardButton.hidden = false;
    discardButton.disabled = false;
    const label = discardButton.querySelector('span');
    if (label) label.textContent = t('fieldPhoto.delete');
};

async function deleteSubmittedFieldPhotoThanks() {
    const status = document.getElementById('field-photo-thanks-status');
    const discardButton = document.getElementById('field-photo-thanks-discard');
    const token = String(lastFieldPhotoThanksToken || '').trim();
    const photoIds = lastFieldPhotoThanksPhotoIds.map(safeFieldPhotoId).filter(Boolean);
    const tokenError = validateFieldPhotoEditToken(token, { required: true });
    if (tokenError || !photoIds.length) {
        if (status) status.textContent = tokenError || t('fieldPhoto.deleteError');
        return;
    }
    const confirmed = await confirmAction({
        title: t('fieldPhoto.deleteTitle'),
        message: t('fieldPhoto.deleteConfirm', { n: photoIds.length }),
        confirmLabel: t('fieldPhoto.delete'),
    });
    if (!confirmed) return;

    if (discardButton) discardButton.disabled = true;
    if (status) status.textContent = t('modal.photoReview.deleting');
    try {
        const data = await apiPostJson(`${FIELD_PHOTOS_URL}/owner-delete`, {
            photo_ids: photoIds,
            edit_token: token,
        });
        if (data.status !== 'ok') {
            throw new Error(data.error || t('fieldPhoto.deleteError'));
        }
        clearFieldPhotoThanksDraftState();
        await loadFieldPhotos();
        closeModal(document.getElementById('modal-field-photo-thanks'));
        statusEl.textContent = t('modal.photoReview.deleted');
        statusEl.className = 'ok';
    } catch (err) {
        if (status) status.textContent = apiErrorMessage(err, t('fieldPhoto.deleteError'));
        if (discardButton) discardButton.disabled = false;
    }
}

const originalDiscardFieldPhotoThanksDraft = discardFieldPhotoThanksDraft;
discardFieldPhotoThanksDraft = async function discardFieldPhotoThanksDraft() {
    if (fieldPhotoThanksSubmittedCanDelete) {
        await deleteSubmittedFieldPhotoThanks();
        return;
    }
    await originalDiscardFieldPhotoThanksDraft();
};
