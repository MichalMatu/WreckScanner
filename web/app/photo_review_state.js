function currentPhotoReviewSnapshot() {
    if (!activePhotoReview) return null;
    return JSON.stringify({
        redactions: photoReviewRedactions.map(normalizePhotoReviewRedaction).filter(Boolean),
        vehicleInsuranceStatus: activePhotoReview.issue_type === FIELD_PHOTO_ISSUE_TYPE_VEHICLE
            ? photoReviewVehicleInsuranceStatus()
            : null,
    });
}

function capturePhotoReviewSnapshot() {
    photoReviewSavedSnapshot = currentPhotoReviewSnapshot();
}

function photoReviewHasUnsavedChanges() {
    return photoReviewSavedSnapshot !== null && currentPhotoReviewSnapshot() !== photoReviewSavedSnapshot;
}

function discardPhotoReviewChanges() {
    if (!activePhotoReview) return;
    photoReviewRedactions = (Array.isArray(activePhotoReview.redactions) ? activePhotoReview.redactions : [])
        .map(normalizePhotoReviewRedaction)
        .filter(Boolean);
    activePhotoReviewRedactionIndex = photoReviewRedactions.length ? photoReviewRedactions.length - 1 : -1;
    photoReviewDraftRect = null;
    updatePhotoReviewVehicleInsuranceUi();
    drawPhotoReviewCanvas();
    capturePhotoReviewSnapshot();
}

async function confirmPhotoReviewDiscard() {
    if (!photoReviewHasUnsavedChanges()) return true;
    if (photoReviewActionInFlight) return false;
    const confirmed = await confirmAction({
        title: apiLocalizedText('modal.photoReview.unsavedTitle', 'Niezapisane zmiany'),
        message: apiLocalizedText(
            'modal.photoReview.unsavedConfirm',
            'Odrzucić niezapisane obszary anonimizacji i zmianę statusu OC?',
        ),
        confirmLabel: apiLocalizedText('modal.photoReview.discardChanges', 'Odrzuć zmiany'),
    });
    if (confirmed) discardPhotoReviewChanges();
    return confirmed;
}
