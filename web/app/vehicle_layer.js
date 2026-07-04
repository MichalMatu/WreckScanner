let vehicleMarkers = [];
let vehicleLayerVisible = true;
const VEHICLE_STATUS_FILTER_ALL = 'all';
const VEHICLE_STATUS_FILTER_UNINSURED = 'uninsured';
const VEHICLE_STATUS_FILTER_LONG_STANDING = 'long-standing';
const VEHICLE_STATUS_FILTER_UNKNOWN = FIELD_PHOTO_VEHICLE_INSURANCE_STATUS_UNKNOWN;
const VEHICLE_STATUS_FILTERS = new Set([
    VEHICLE_STATUS_FILTER_ALL,
    VEHICLE_STATUS_FILTER_UNINSURED,
    VEHICLE_STATUS_FILTER_LONG_STANDING,
    VEHICLE_STATUS_FILTER_UNKNOWN,
]);
let vehicleStatusFilter = VEHICLE_STATUS_FILTER_ALL;
let pendingVehiclePhotoFocusId = '';
let vehiclePhotoFocusDone = false;

try {
    pendingVehiclePhotoFocusId = String(new URLSearchParams(window.location.search).get('photo') || '')
        .replace(/[^A-Za-z0-9_-]/g, '');
    vehiclePhotoFocusDone = !pendingVehiclePhotoFocusId;
} catch (_) {
    pendingVehiclePhotoFocusId = '';
    vehiclePhotoFocusDone = true;
}

function clearVehicleMarkers() {
    vehicleMarkers.forEach(marker => map.removeLayer(marker));
    vehicleMarkers = [];
}

function vehicleLayerAllowed() {
    return vehicleLayerVisible && publicLayerAllowed(PUBLIC_LAYER_KEYS.vehicles);
}

function vehiclePhotoIsApproved(photo) {
    return fieldPhotoIssueType(photo) === FIELD_PHOTO_ISSUE_TYPE_VEHICLE
        && fieldPhotoReviewStatus(photo) === 'approved';
}

function emptyVehicleGroup(lat, lon) {
    return { lat, lon, photos: [] };
}

function nearestVehicleGroup(groups, lat, lon) {
    let nearest = null;
    groups.forEach(group => {
        const distanceM = metersBetween(group.lat, group.lon, lat, lon);
        if (distanceM > FIELD_PHOTO_GROUP_RADIUS_M) return;
        if (!nearest || distanceM < nearest.distanceM) nearest = { group, distanceM };
    });
    return nearest?.group || null;
}

function addVehiclePhotoToGroup(group, photo, lat, lon) {
    group.photos.push(photo);
    const count = group.photos.length;
    group.lat = ((group.lat * (count - 1)) + lat) / count;
    group.lon = ((group.lon * (count - 1)) + lon) / count;
}

function buildVehicleGroups(photos = fieldPhotoLayerData) {
    const groups = [];
    (photos || []).filter(vehiclePhotoIsApproved).forEach(photo => {
        const lat = Number(photo.lat);
        const lon = Number(photo.lon);
        if (!Number.isFinite(lat) || !Number.isFinite(lon)) return;
        let group = nearestVehicleGroup(groups, lat, lon);
        if (!group) {
            group = emptyVehicleGroup(lat, lon);
            groups.push(group);
        }
        addVehiclePhotoToGroup(group, photo, lat, lon);
    });
    return groups;
}

function vehicleGroupPhotoCount(group) {
    return Array.isArray(group?.photos) ? group.photos.length : 0;
}

function vehicleGroupHasPhotoId(group, photoId) {
    const safePhotoId = String(photoId || '').replace(/[^A-Za-z0-9_-]/g, '');
    return Boolean(safePhotoId) && (group.photos || []).some(photo => safeFieldPhotoId(photo.id) === safePhotoId);
}

function focusVehicleMarkerFromUrl(group, marker) {
    if (vehiclePhotoFocusDone || !pendingVehiclePhotoFocusId || !vehicleGroupHasPhotoId(group, pendingVehiclePhotoFocusId)) {
        return;
    }
    vehiclePhotoFocusDone = true;
    requestAnimationFrame(() => {
        if (!map.hasLayer(marker)) return;
        const targetZoom = Math.max(Number(map.getZoom()) || 0, 19);
        map.setView([group.lat, group.lon], targetZoom, { animate: false });
        marker.openPopup();
    });
}

function vehicleLoosePhotoActions(group, { includeReport = true, includeUpload = true } = {}) {
    const photos = group.photos || [];
    if (!photos.length) return [];
    const lat = Number(group.lat);
    const lon = Number(group.lon);
    const encodedPhotoIds = encodedFieldPhotoIdsForGroup(group);
    const coordinatesOk = Number.isFinite(lat) && Number.isFinite(lon) && encodedPhotoIds;
    const canCreateReport = includeReport
        && coordinatesOk
        && publicFeatureAllowed(PUBLIC_FEATURE_KEYS.reportPackages);
    const canAddFieldPhotosHere = includeUpload
        && coordinatesOk
        && publicFeatureAllowed(PUBLIC_FEATURE_KEYS.photoUploads)
        && fieldPhotoIssueAllowed(FIELD_PHOTO_ISSUE_TYPE_VEHICLE);
    const ownerButton = encodedPhotoIds
        ? mapPopupIconAction(
            'map-popup-action--primary',
            t('fieldPhoto.editMyPhoto'),
            `openFieldPhotoOwnerEditor('${encodedPhotoIds}')`,
            'M11 17h2v-6h-2v6zm0-8h2V7h-2v2zm1-7a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm0 18a8 8 0 1 1 0-16 8 8 0 0 1 0 16z'
        )
        : '';
    const reportButton = canCreateReport
        ? mapPopupIconAction(
            'map-popup-action--report',
            t('fieldPhoto.reportPackage'),
            `openFieldPhotoGroupReport(${lat}, ${lon}, '${encodedPhotoIds}', this)`,
            'M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm1 7V3.5L18.5 9H15zM8 13h8v2H8v-2zm0 4h8v2H8v-2z'
        )
        : '';
    const photoButton = canAddFieldPhotosHere
        ? mapPopupIconAction(
            'map-popup-action--primary',
            t('fieldPhoto.addPhotosHere'),
            `openFieldPhotoGroupPhotoUpload(${lat}, ${lon}, '${encodedPhotoIds}', '${FIELD_PHOTO_ISSUE_TYPE_VEHICLE}', this)`,
            'M5 7h2.8L9.4 5h5.2l1.6 2H19c1.1 0 2 .9 2 2v10c0 1.1-.9 2-2 2H5c-1.1 0-2-.9-2-2V9c0-1.1.9-2 2-2zm7 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zm5-5h-2v2h-2v2h2v2h2v-2h2v-2h-2v-2z'
        )
        : '';
    const reviewButton = adminAuthenticated && encodedPhotoIds
        ? mapPopupIconAction(
            'map-popup-action--primary',
            t('fieldPhoto.reviewPhotos'),
            `openPhotoReviewForFieldPhotoGroup('${encodedPhotoIds}')`,
            'M4 5h16v14H4V5zm2 2v10h12V7H6zm2 8h8l-2.5-3.2-1.8 2.2-1.3-1.5L8 15zm10-9.5 1.1-1.1 1.5 1.5-1.1 1.1-1.5-1.5zm-6.5 6.5L18 5.5 19.5 7 13 13.5H11.5V12z'
        )
        : '';
    const deleteButton = adminAuthenticated && encodedPhotoIds
        ? mapPopupIconAction(
            'map-popup-action--danger',
            t('fieldPhoto.delete'),
            `deleteFieldPhotoGroup('${encodedPhotoIds}', this)`,
            'M9 3v1H4v2h16V4h-5V3H9zm-3 5l1 13a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-13H6zm4 3h1v9h-1v-9zm3 0h1v9h-1v-9z'
        )
        : '';
    return [ownerButton, reportButton, photoButton, reviewButton, deleteButton];
}

function vehicleGroupPreviews(group) {
    return fieldPhotoGroupPreviews(group.photos);
}

function vehicleGroupLinks(group) {
    const photos = group.photos || [];
    return fieldPhotoGroupLinks(group, photos);
}

function vehicleGroupActions(group) {
    return vehicleLoosePhotoActions(group);
}

function vehicleGroupInsuranceStatus(group) {
    const statuses = (group.photos || []).map(photo => vehicleInsuranceStatus(photo.vehicle_insurance_status));
    if (statuses.includes('uninsured')) return 'uninsured';
    if (statuses.includes('insured')) return 'insured';
    return statuses.length ? FIELD_PHOTO_VEHICLE_INSURANCE_STATUS_UNKNOWN : '';
}

function vehicleGroupIsLongStanding(group, nowMs = Date.now()) {
    const startTimestampMs = fieldPhotoGroupStartTimestamp(group.photos, nowMs);
    return Number.isFinite(startTimestampMs) && nowMs - startTimestampMs >= VEHICLE_LONG_STANDING_MS;
}

function normalizeVehicleStatusFilter(filter) {
    const safeFilter = String(filter || '');
    return VEHICLE_STATUS_FILTERS.has(safeFilter) ? safeFilter : VEHICLE_STATUS_FILTER_ALL;
}

function vehicleGroupMatchesStatusFilter(group, filter = vehicleStatusFilter) {
    switch (normalizeVehicleStatusFilter(filter)) {
        case VEHICLE_STATUS_FILTER_UNINSURED:
            return vehicleGroupInsuranceStatus(group) === 'uninsured';
        case VEHICLE_STATUS_FILTER_LONG_STANDING:
            return vehicleGroupIsLongStanding(group);
        case VEHICLE_STATUS_FILTER_UNKNOWN:
            return vehicleGroupInsuranceStatus(group) === FIELD_PHOTO_VEHICLE_INSURANCE_STATUS_UNKNOWN;
        case VEHICLE_STATUS_FILTER_ALL:
        default:
            return true;
    }
}

function visibleVehicleGroups(photos = fieldPhotoLayerData) {
    if (!publicLayerAllowed(PUBLIC_LAYER_KEYS.vehicles)) return [];
    return buildVehicleGroups(photos).filter(group =>
        vehicleGroupPhotoCount(group) > 0
        && vehicleGroupMatchesStatusFilter(group)
    );
}

function updateVehicleStatusFilterControls() {
    document.querySelectorAll('[data-vehicle-status-filter]').forEach(button => {
        const active = normalizeVehicleStatusFilter(button.dataset.vehicleStatusFilter) === vehicleStatusFilter;
        button.classList.toggle('is-active', active);
        button.setAttribute('aria-pressed', active ? 'true' : 'false');
    });
}

function setVehicleStatusFilter(filter) {
    const nextFilter = normalizeVehicleStatusFilter(filter);
    if (nextFilter === vehicleStatusFilter) {
        updateVehicleStatusFilterControls();
        return;
    }
    vehicleStatusFilter = nextFilter;
    refreshVehicleLayer();
    updateVehicleStatusFilterControls();
}

function vehiclePhotoPopup(group) {
    const photoCount = vehicleGroupPhotoCount(group);
    const title = photoCount > 1
        ? t('vehicle.popup.photoGroupTitle', { n: photoCount })
        : t('vehicle.popup.photoTitle');
    const previews = vehicleGroupPreviews(group);
    return mapPopup(`
            ${popupHeader(title, [vehicleInsuranceHeaderBadge(vehicleGroupInsuranceStatus(group)), popupElapsedAgeBadge(group.photos)])}
            ${popupPhotoSection('', previews, { className: 'map-popup-photo-grid--field', total: photoCount, showHeader: false })}
            ${vehicleGroupLinks(group)}
            ${popupActions(vehicleGroupActions(group))}
    `, mapPopupMediaModifiers(previews, 'map-popup--vehicle-photo'));
}

function vehicleGroupPopup(group) {
    return vehiclePhotoPopup(group);
}

function placeVehicleMarkers() {
    clearVehicleMarkers();
    if (!vehicleLayerAllowed()) return;
    visibleVehicleGroups().forEach(group => {
        const canDrag = adminAuthenticated && group.photos.length > 0;
        const marker = L.marker([group.lat, group.lon], {
            icon: vehicleIcon(
                vehicleGroupPhotoCount(group),
                'approved',
                vehicleGroupInsuranceStatus(group),
                vehicleGroupIsLongStanding(group)
            ),
            zIndexOffset: 1200,
            draggable: canDrag,
            autoPan: canDrag,
        }).addTo(map).bindPopup(vehicleGroupPopup(group), mapPopupOptions());
        if (canDrag) {
            marker.on('dragstart', () => marker.closePopup());
            marker.on('dragend', () => updateFieldPhotoGroupLocation(
                { ...group, issueType: FIELD_PHOTO_ISSUE_TYPE_VEHICLE },
                marker
            ));
        }
        vehicleMarkers.push(marker);
        focusVehicleMarkerFromUrl(group, marker);
    });
}

function refreshVehicleLayer() {
    placeVehicleMarkers();
    updateLayerCounters();
    updateVehicleStatusFilterControls();
}

function toggleVehicleLayer(visible) {
    vehicleLayerVisible = Boolean(visible);
    refreshVehicleLayer();
}
