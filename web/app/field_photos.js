let fieldPhotoMarkers = [];
let fieldPhotoLayerData = [];

function clearFieldPhotoMarkers() {
    fieldPhotoMarkers.forEach(m => map.removeLayer(m));
    fieldPhotoMarkers = [];
}

function safeFieldPhotoId(value) {
    return String(value ?? '').replace(/[^A-Za-z0-9_-]/g, '');
}

function fieldPhotoIssueType(photo) {
    const issueType = String(photo?.issue_type || FIELD_PHOTO_ISSUE_TYPE_VEHICLE);
    return FIELD_PHOTO_ISSUE_TYPES.has(issueType) ? issueType : FIELD_PHOTO_ISSUE_TYPE_VEHICLE;
}

function fieldPhotoIssueLabel(issueType) {
    return t(`fieldPhoto.issueType.${FIELD_PHOTO_ISSUE_TYPES.has(issueType) ? issueType : FIELD_PHOTO_ISSUE_TYPE_VEHICLE}`);
}

function fieldPhotoIssueAllowed(issueType) {
    const safeIssueType = FIELD_PHOTO_ISSUE_TYPES.has(issueType) ? issueType : FIELD_PHOTO_ISSUE_TYPE_VEHICLE;
    return publicLayerAllowed(fieldPhotoPublicLayerKey(safeIssueType));
}

function fieldPhotoAnyIssueAllowed() {
    return Array.from(FIELD_PHOTO_ISSUE_TYPES).some(issueType => fieldPhotoIssueAllowed(issueType));
}

function fieldPhotoIssueVisible(issueType) {
    const safeIssueType = FIELD_PHOTO_ISSUE_TYPES.has(issueType) ? issueType : FIELD_PHOTO_ISSUE_TYPE_VEHICLE;
    return fieldPhotoIssueAllowed(safeIssueType) && fieldPhotoIssueFilters[safeIssueType] !== false;
}

function fieldPhotoReviewStatus(photo) {
    const status = String(photo?.public_review_status || 'approved');
    return status === 'pending' || status === 'rejected' ? status : 'approved';
}

function fieldPhotoGroupKind(photo) {
    const status = fieldPhotoReviewStatus(photo);
    if (status === 'pending') return adminAuthenticated ? 'admin-pending' : 'public-pending';
    return 'approved';
}

function fieldPhotoGroupReviewStatus(group) {
    return group?.reviewStatus === 'pending' ? 'pending' : 'approved';
}

function updateFieldPhotoIssueOptions() {
    const select = document.getElementById('field-photo-issue-type');
    if (!(select instanceof HTMLSelectElement)) return;
    let firstEnabled = '';
    Array.from(select.options).forEach(option => {
        const issueType = FIELD_PHOTO_ISSUE_TYPES.has(option.value) ? option.value : FIELD_PHOTO_ISSUE_TYPE_VEHICLE;
        const enabled = fieldPhotoIssueAllowed(issueType);
        option.disabled = !enabled;
        option.hidden = !enabled;
        if (enabled && !firstEnabled) firstEnabled = option.value;
    });
    select.disabled = !firstEnabled;
    if (firstEnabled && (!FIELD_PHOTO_ISSUE_TYPES.has(select.value) || select.selectedOptions[0]?.disabled)) {
        select.value = firstEnabled;
    }
    if (typeof updateFieldPhotoVehicleInsuranceUi === 'function') updateFieldPhotoVehicleInsuranceUi();
}

function filteredFieldPhotos(photos = fieldPhotoLayerData) {
    return (photos || []).filter(photo => {
        const issueType = fieldPhotoIssueType(photo);
        const reviewStatus = fieldPhotoReviewStatus(photo);
        if (reviewStatus === 'pending') {
            return pendingFieldPhotoLayerVisible && publicLayerAllowed(PUBLIC_LAYER_KEYS.fieldPhotoPending);
        }
        if (issueType === FIELD_PHOTO_ISSUE_TYPE_VEHICLE) return false;
        return fieldPhotoIssueVisible(issueType);
    });
}

function groupFieldPhotos(photos) {
    const groups = [];
    (photos || []).forEach(photo => {
        const lat = Number(photo.lat);
        const lon = Number(photo.lon);
        if (!Number.isFinite(lat) || !Number.isFinite(lon)) return;
        const issueType = fieldPhotoIssueType(photo);
        const reviewStatus = fieldPhotoReviewStatus(photo);
        const groupKind = fieldPhotoGroupKind(photo);
        let group = groups.find(candidate =>
            candidate.issueType === issueType
            && candidate.groupKind === groupKind
            && metersBetween(candidate.lat, candidate.lon, lat, lon) <= FIELD_PHOTO_GROUP_RADIUS_M
        );
        if (!group) {
            group = { lat, lon, issueType, reviewStatus, groupKind, photos: [] };
            groups.push(group);
        }
        group.photos.push(photo);
        const count = group.photos.length;
        group.lat = ((group.lat * (count - 1)) + lat) / count;
        group.lon = ((group.lon * (count - 1)) + lon) / count;
    });
    return groups;
}

function countVehicleLayerGroups() {
    if (!publicLayerAllowed(PUBLIC_LAYER_KEYS.vehicles)) return 0;
    return visibleVehicleGroups().length;
}

function countFieldPhotoIssueLayerGroups(issueType) {
    if (!publicLayerAllowed(fieldPhotoPublicLayerKey(issueType))) return 0;
    return groupFieldPhotos((fieldPhotoLayerData || []).filter(photo =>
        fieldPhotoIssueType(photo) === issueType
        && fieldPhotoReviewStatus(photo) !== 'pending'
    )).length;
}

function countPendingFieldPhotoLayerGroups() {
    if (!publicLayerAllowed(PUBLIC_LAYER_KEYS.fieldPhotoPending)) return 0;
    return groupFieldPhotos((fieldPhotoLayerData || []).filter(photo =>
        fieldPhotoReviewStatus(photo) === 'pending'
    )).length;
}

function updateLayerCountBadge(id, count, tooltipKey) {
    const badge = document.getElementById(id);
    if (!badge) return;
    const safeCount = Number.isFinite(count) ? count : 0;
    const tooltip = t(tooltipKey, { n: safeCount });
    badge.textContent = String(safeCount);
    badge.title = tooltip;
    badge.setAttribute('aria-label', tooltip);
}

function updateLayerCounters() {
    updateLayerCountBadge('layer-count-vehicles', countVehicleLayerGroups(), 'layers.countVehiclesTooltip');
    updateLayerCountBadge(
        'layer-count-field-photo-infrastructure',
        countFieldPhotoIssueLayerGroups('infrastructure'),
        'layers.countFieldPhotoInfrastructureTooltip'
    );
    updateLayerCountBadge(
        'layer-count-field-photo-smoke',
        countFieldPhotoIssueLayerGroups('smoke'),
        'layers.countFieldPhotoSmokeTooltip'
    );
    updateLayerCountBadge(
        'layer-count-field-photo-pending',
        countPendingFieldPhotoLayerGroups(),
        'layers.countFieldPhotoPendingTooltip'
    );
}

function placeFieldPhotos(photos = fieldPhotoLayerData) {
    clearFieldPhotoMarkers();
    groupFieldPhotos(filteredFieldPhotos(photos)).forEach(group => {
        const reviewStatus = fieldPhotoGroupReviewStatus(group);
        const marker = L.marker([group.lat, group.lon], {
            icon: reviewStatus === 'pending' ? pendingSubmissionIcon() : fieldPhotoIcon(group.photos.length, group.issueType),
            zIndexOffset: 1400,
            draggable: adminAuthenticated,
            autoPan: adminAuthenticated,
        }).addTo(map).bindPopup(fieldPhotoGroupPopup(group), mapPopupOptions());
        if (adminAuthenticated) {
            marker.on('dragstart', () => marker.closePopup());
            marker.on('dragend', () => updateFieldPhotoGroupLocation(group, marker));
        }
        fieldPhotoMarkers.push(marker);
    });
}

async function loadFieldPhotos() {
    try {
        const data = await apiJson(`${FIELD_PHOTOS_URL}?ts=${Date.now()}`, { cache: 'no-store' });
        if (data.status === 'ok') {
            fieldPhotoLayerData = data.photos || [];
            placeFieldPhotos(fieldPhotoLayerData);
            placeVehicleMarkers();
            updateLayerCounters();
        }
    } catch (_) {}
}

function toggleFieldPhotoIssueFilter(issueType, visible) {
    const safeIssueType = FIELD_PHOTO_ISSUE_TYPES.has(issueType) ? issueType : FIELD_PHOTO_ISSUE_TYPE_VEHICLE;
    fieldPhotoIssueFilters[safeIssueType] = Boolean(visible);
    placeFieldPhotos(fieldPhotoLayerData);
    updateFieldPhotoIssueOptions();
    updateLayerCounters();
}

function togglePendingFieldPhotoLayer(visible) {
    pendingFieldPhotoLayerVisible = Boolean(visible);
    placeFieldPhotos(fieldPhotoLayerData);
    updateLayerCounters();
}
