function countBadge(count, className) {
    const numericCount = Math.max(0, Math.floor(Number(count) || 0));
    if (numericCount <= 0) return '';
    return `<span class="map-pin-count ${className}">${numericCount}</span>`;
}

function vehicleIcon(photoCount = 0, reviewStatus = 'approved') {
    const numericCount = Math.max(0, Math.floor(Number(photoCount) || 0));
    const badge = countBadge(numericCount, 'vehicle-pin-count');
    const safeStatus = reviewStatus === 'pending' || reviewStatus === 'rejected' ? reviewStatus : 'approved';
    const classes = ['vehicle-pin', `vehicle-pin--${safeStatus}`];
    if (numericCount > 0) classes.push('vehicle-pin--with-photos');
    const className = classes.join(' ');
    const html = `<div class="${className}">${badge}</div>`;
    return L.divIcon({ html, className: 'map-pin-icon', iconSize: [34,34], iconAnchor:[17,34] });
}

function fieldPhotoIcon(count = 1, issueType = FIELD_PHOTO_ISSUE_TYPE_VEHICLE) {
    const photoCount = Math.max(1, Number(count) || 1);
    const badge = photoCount > 1 ? countBadge(photoCount, 'field-photo-pin-count') : '';
    const safeIssueType = FIELD_PHOTO_ISSUE_TYPES.has(issueType) ? issueType : FIELD_PHOTO_ISSUE_TYPE_VEHICLE;
    const html = `<div class="field-photo-pin field-photo-pin--${safeIssueType}">${badge}</div>`;
    return L.divIcon({ html, className: 'map-pin-icon', iconSize: [34,34], iconAnchor:[17,34] });
}

function pendingSubmissionIcon() {
    const html = '<div class="pending-submission-pin pending-submission-pin--photo"></div>';
    return L.divIcon({ html, className: 'map-pin-icon', iconSize: [34,34], iconAnchor:[17,34] });
}

function pendingFieldPhotoPopup(group) {
    const lat = Number(group.lat);
    const lon = Number(group.lon);
    const encodedPhotoIds = encodedFieldPhotoIdsForGroup(group);
    const ownerButton = encodedPhotoIds
        ? mapPopupIconAction(
            'map-popup-action--photo',
            t('fieldPhoto.editMyPhoto'),
            `openFieldPhotoOwnerEditor('${encodedPhotoIds}')`,
            'M11 17h2v-6h-2v6zm0-8h2V7h-2v2zm1-7a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm0 18a8 8 0 1 1 0-16 8 8 0 0 1 0 16z'
        )
        : '';
    return `
        <div class="map-popup map-popup--pending-submission">
            ${popupHeader(t('pendingSubmission.photoTitle'), t('pendingSubmission.status'))}
            ${popupMeta([
                t('fieldPhoto.pendingPublicHint'),
                t('pendingSubmission.coords', { lat: lat.toFixed(6), lon: lon.toFixed(6) }),
            ])}
            ${popupActions([ownerButton])}
        </div>
    `;
}
