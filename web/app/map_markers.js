let pendingSubmissionLayer = L.layerGroup().addTo(map);
let pendingSubmissionMarkers = [];
const PENDING_SUBMISSION_MARKER_LIMIT = 25;

function countBadge(count, className) {
    const numericCount = Math.max(0, Math.floor(Number(count) || 0));
    if (numericCount <= 0) return '';
    return `<span class="map-pin-count ${className}">${numericCount}</span>`;
}

function wreckIcon(photoCount = 0, reviewStatus = 'approved') {
    const numericCount = Math.max(0, Math.floor(Number(photoCount) || 0));
    const badge = countBadge(numericCount, 'saved-wreck-pin-count');
    const safeStatus = reviewStatus === 'pending' || reviewStatus === 'rejected' ? reviewStatus : 'approved';
    const classes = ['saved-wreck-pin', `saved-wreck-pin--${safeStatus}`];
    if (numericCount > 0) classes.push('saved-wreck-pin--with-photos');
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

function pendingSubmissionIcon(kind = 'wreck') {
    const safeKind = kind === 'photo' ? 'photo' : 'wreck';
    const html = `<div class="pending-submission-pin pending-submission-pin--${safeKind}"></div>`;
    return L.divIcon({ html, className: 'map-pin-icon', iconSize: [34,34], iconAnchor:[17,34] });
}

function pendingWreckSubmissionPopup(lat, lon) {
    return `
        <div class="map-popup map-popup--pending-submission">
            ${popupHeader(t('pendingSubmission.wreckTitle'), t('pendingSubmission.status'))}
            ${popupMeta([
                t('pendingSubmission.reviewHint'),
                t('pendingSubmission.coords', { lat: Number(lat).toFixed(6), lon: Number(lon).toFixed(6) }),
            ])}
        </div>
    `;
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

function addPendingSubmissionMarker({ lat, lon } = {}) {
    const latNumber = Number(lat);
    const lonNumber = Number(lon);
    if (!Number.isFinite(latNumber) || !Number.isFinite(lonNumber)) return null;

    const marker = L.marker([latNumber, lonNumber], {
        icon: pendingSubmissionIcon('wreck'),
        zIndexOffset: 1800,
    }).bindPopup(pendingWreckSubmissionPopup(latNumber, lonNumber), { maxWidth: 300 });
    pendingSubmissionLayer.addLayer(marker);
    pendingSubmissionMarkers.push(marker);
    while (pendingSubmissionMarkers.length > PENDING_SUBMISSION_MARKER_LIMIT) {
        pendingSubmissionLayer.removeLayer(pendingSubmissionMarkers.shift());
    }
    marker.openPopup();
    return marker;
}

function clearPendingSubmissionMarkers() {
    pendingSubmissionMarkers.forEach(marker => pendingSubmissionLayer.removeLayer(marker));
    pendingSubmissionMarkers = [];
}
