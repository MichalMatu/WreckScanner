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

function photoReviewVehicleResolutionStatus() {
    const status = String(activePhotoReview?.vehicle_resolution_status || FIELD_PHOTO_VEHICLE_RESOLUTION_STATUS_ACTIVE);
    return FIELD_PHOTO_VEHICLE_RESOLUTION_STATUSES.has(status)
        ? status
        : FIELD_PHOTO_VEHICLE_RESOLUTION_STATUS_ACTIVE;
}

function photoReviewVehicleResolutionNextStatus() {
    return photoReviewVehicleResolutionStatus() === FIELD_PHOTO_VEHICLE_RESOLUTION_STATUS_REMOVED
        ? FIELD_PHOTO_VEHICLE_RESOLUTION_STATUS_ACTIVE
        : FIELD_PHOTO_VEHICLE_RESOLUTION_STATUS_REMOVED;
}

function photoReviewItemIsRemoved(item) {
    return item?.issue_type === FIELD_PHOTO_ISSUE_TYPE_VEHICLE
        && String(item?.vehicle_resolution_status || '') === FIELD_PHOTO_VEHICLE_RESOLUTION_STATUS_REMOVED;
}

function updatePhotoReviewVehicleResolutionAction() {
    const button = document.getElementById('photo-review-resolution-toggle');
    const label = document.getElementById('photo-review-resolution-label');
    if (!button) return;
    const show = photoReviewMode === 'admin'
        && activePhotoReview?.issue_type === FIELD_PHOTO_ISSUE_TYPE_VEHICLE
        && activePhotoReview?.public_review_status === 'approved'
        && Boolean(photoReviewEndpoint(activePhotoReview));
    button.hidden = !show;
    button.disabled = photoReviewActionInFlight || !show;
    if (!show) return;
    const nextStatus = photoReviewVehicleResolutionNextStatus();
    const removedNext = nextStatus === FIELD_PHOTO_VEHICLE_RESOLUTION_STATUS_REMOVED;
    const title = t(removedNext ? 'modal.photoReview.markRemoved' : 'modal.photoReview.markActive');
    button.classList.toggle('review-action-btn--resolved', !removedNext);
    button.dataset.vehicleResolutionStatus = nextStatus;
    button.title = title;
    button.setAttribute('aria-label', title);
    if (label) {
        label.textContent = t(removedNext
            ? 'modal.photoReview.markRemovedShort'
            : 'modal.photoReview.markActiveShort');
    }
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

async function togglePhotoReviewVehicleResolution() {
    if (photoReviewActionInFlight || photoReviewMode !== 'admin') return;
    const endpoint = photoReviewEndpoint(activePhotoReview);
    if (
        !endpoint
        || activePhotoReview?.issue_type !== FIELD_PHOTO_ISSUE_TYPE_VEHICLE
        || activePhotoReview?.public_review_status !== 'approved'
    ) {
        return;
    }
    if (!(await confirmPhotoReviewDiscard())) return;
    const savedPhotoId = activePhotoReview.id;
    const savedPhotoIndex = photoReviewActiveIndex(savedPhotoId);
    const list = document.getElementById('photo-review-list');
    const savedScrollTop = list?.scrollTop;
    const nextStatus = photoReviewVehicleResolutionNextStatus();
    setPhotoReviewActionInFlight(true);
    setPhotoReviewStatusMessage(t('modal.photoReview.saving'));
    try {
        const data = await apiPatchJson(endpoint, { vehicle_resolution_status: nextStatus });
        if (data.status !== 'ok') {
            throw new Error(data.error || t('modal.photoReview.saveError'));
        }
        setPhotoReviewStatusMessage(t(nextStatus === FIELD_PHOTO_VEHICLE_RESOLUTION_STATUS_REMOVED
            ? 'modal.photoReview.markedRemoved'
            : 'modal.photoReview.markedActive'));
        await loadFieldPhotos();
        await loadPhotoReviewQueue({
            preferredPhotoId: savedPhotoId,
            fallbackIndex: savedPhotoIndex,
            preserveScroll: Number.isFinite(savedScrollTop),
        });
    } catch (err) {
        setPhotoReviewStatusMessage(apiErrorMessage(err, t('modal.photoReview.saveError')));
    } finally {
        setPhotoReviewActionInFlight(false);
    }
}
