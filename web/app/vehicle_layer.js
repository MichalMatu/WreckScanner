let vehicleMarkers = [];
let vehicleLayerVisible = true;

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
            'map-popup-action--photo',
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
            'map-popup-action--photo',
            t('fieldPhoto.addPhotosHere'),
            `openFieldPhotoGroupPhotoUpload(${lat}, ${lon}, '${encodedPhotoIds}', '${FIELD_PHOTO_ISSUE_TYPE_VEHICLE}', this)`,
            'M5 7h2.8L9.4 5h5.2l1.6 2H19c1.1 0 2 .9 2 2v10c0 1.1-.9 2-2 2H5c-1.1 0-2-.9-2-2V9c0-1.1.9-2 2-2zm7 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zm5-5h-2v2h-2v2h2v2h2v-2h2v-2h-2v-2z'
        )
        : '';
    const reviewButton = adminAuthenticated && encodedPhotoIds
        ? mapPopupIconAction(
            'map-popup-action--photo',
            t('fieldPhoto.reviewPhotos'),
            `openPhotoReviewForFieldPhotoGroup('${encodedPhotoIds}')`,
            'M4 5h16v14H4V5zm2 2v10h12V7H6zm2 8h8l-2.5-3.2-1.8 2.2-1.3-1.5L8 15zm10-9.5 1.1-1.1 1.5 1.5-1.1 1.1-1.5-1.5zm-6.5 6.5L18 5.5 19.5 7 13 13.5H11.5V12z'
        )
        : '';
    const deleteButton = adminAuthenticated && encodedPhotoIds
        ? mapPopupIconAction(
            'map-popup-action--delete',
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

function vehicleGroupMeta(group) {
    const photos = group.photos || [];
    const firstPhoto = photos[0] || {};
    return popupMeta([
        photos.length === 1
            ? t('fieldPhoto.popup.capturedAt', { date: firstPhoto.captured_at || t('fieldPhoto.noCapturedAt') })
            : '',
    ]);
}

function vehicleGroupLinks(group) {
    const photos = group.photos || [];
    return fieldPhotoGroupLinks(group, photos);
}

function vehicleGroupActions(group) {
    return vehicleLoosePhotoActions(group);
}

function vehiclePhotoPopup(group) {
    const photoCount = vehicleGroupPhotoCount(group);
    const title = photoCount > 1
        ? t('vehicle.popup.photoGroupTitle', { n: photoCount })
        : t('vehicle.popup.photoTitle');
    const previews = vehicleGroupPreviews(group);
    return `
        <div class="map-popup map-popup--vehicle-photo">
            ${popupHeader(title)}
            ${vehicleGroupMeta(group)}
            ${popupPhotoSection('', previews, { className: 'map-popup-photo-grid--field', total: photoCount, showHeader: false })}
            ${vehicleGroupLinks(group)}
            ${popupActions(vehicleGroupActions(group))}
        </div>
    `;
}

function vehicleGroupPopup(group) {
    return vehiclePhotoPopup(group);
}

function placeVehicleMarkers() {
    clearVehicleMarkers();
    if (!vehicleLayerAllowed()) return;
    buildVehicleGroups().forEach(group => {
        const canDrag = adminAuthenticated && group.photos.length > 0;
        const marker = L.marker([group.lat, group.lon], {
            icon: vehicleIcon(vehicleGroupPhotoCount(group)),
            zIndexOffset: 1200,
            draggable: canDrag,
            autoPan: canDrag,
        }).addTo(map).bindPopup(vehicleGroupPopup(group), { maxWidth: vehicleGroupPhotoCount(group) > 1 ? 380 : 320 });
        if (canDrag) {
            marker.on('dragstart', () => marker.closePopup());
            marker.on('dragend', () => updateFieldPhotoGroupLocation(
                { ...group, issueType: FIELD_PHOTO_ISSUE_TYPE_VEHICLE },
                marker
            ));
        }
        vehicleMarkers.push(marker);
    });
}

function refreshVehicleLayer() {
    placeVehicleMarkers();
    updateLayerCounters();
}

function toggleVehicleLayer(visible) {
    vehicleLayerVisible = Boolean(visible);
    refreshVehicleLayer();
}
