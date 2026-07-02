let vehicleMarkers = [];
let savedWreckLayerData = [];
let vehicleLayerVisible = true;

function clearVehicleMarkers() {
    vehicleMarkers.forEach(marker => map.removeLayer(marker));
    vehicleMarkers = [];
}

function safeWreckId(value) {
    return String(value ?? '').replace(/[^A-Za-z0-9_-]/g, '');
}

function vehicleLayerAllowed() {
    return vehicleLayerVisible && publicLayerAllowed(PUBLIC_LAYER_KEYS.vehicles);
}

function vehiclePhotoIsApproved(photo) {
    return fieldPhotoIssueType(photo) === FIELD_PHOTO_ISSUE_TYPE_VEHICLE
        && fieldPhotoReviewStatus(photo) === 'approved';
}

function emptyVehicleGroup(lat, lon) {
    return { lat, lon, wreck: null, photos: [] };
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
    if (group.wreck) return;
    const count = group.photos.length;
    group.lat = ((group.lat * (count - 1)) + lat) / count;
    group.lon = ((group.lon * (count - 1)) + lon) / count;
}

function buildVehicleGroups(wrecks = savedWreckLayerData, photos = fieldPhotoLayerData) {
    const groups = [];
    (wrecks || []).forEach(wreck => {
        const lat = Number(wreck.lat);
        const lon = Number(wreck.lon);
        if (!Number.isFinite(lat) || !Number.isFinite(lon)) return;
        groups.push({ ...emptyVehicleGroup(lat, lon), wreck });
    });
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
    const attachedCount = Number(group?.wreck?.photo_count || 0);
    const looseCount = Array.isArray(group?.photos) ? group.photos.length : 0;
    return attachedCount + looseCount;
}

async function openVehicleCasePhotoUpload(wreckId, lat, lon) {
    if (!publicFeatureAllowed(PUBLIC_FEATURE_KEYS.photoUploads)) return;
    const id = safeWreckId(wreckId);
    const latNumber = Number(lat);
    const lonNumber = Number(lon);
    if (!id || !Number.isFinite(latNumber) || !Number.isFinite(lonNumber)) return;
    if (adminAuthenticated) {
        openWreckPhotoModal(id);
        return;
    }
    await openFieldPhotoUploadModal({
        mapLatLng: L.latLng(latNumber, lonNumber),
        issueType: FIELD_PHOTO_ISSUE_TYPE_VEHICLE,
    });
}

function vehicleCaseActions(wreck) {
    if (!wreck) return [];
    const wreckId = safeWreckId(wreck.id);
    const lat = Number(wreck.lat);
    const lon = Number(wreck.lon);
    const reviewPhotoCount = Number(wreck.review_photo_count || 0);
    const reportButton = mapPopupIconAction(
        'map-popup-action--report',
        t('wreck.reportPackage'),
        `openReportPackageModal('${wreckId}')`,
        'M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm1 7V3.5L18.5 9H15zM8 13h8v2H8v-2zm0 4h8v2H8v-2z'
    );
    const photoButton = publicFeatureAllowed(PUBLIC_FEATURE_KEYS.photoUploads)
        ? mapPopupIconAction(
            'map-popup-action--photo',
            t('wreck.addPhotos'),
            `openVehicleCasePhotoUpload('${wreckId}', ${lat}, ${lon})`,
            'M5 7h2.8L9.4 5h5.2l1.6 2H19c1.1 0 2 .9 2 2v10c0 1.1-.9 2-2 2H5c-1.1 0-2-.9-2-2V9c0-1.1.9-2 2-2zm7 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zm5-5h-2v2h-2v2h2v2h2v-2h2v-2h-2v-2z'
        )
        : '';
    const reviewPhotosButton = adminAuthenticated && reviewPhotoCount > 0
        ? mapPopupIconAction(
            'map-popup-action--photo',
            t('wreck.reviewPhotos'),
            `openPhotoReviewForWreck('${wreckId}')`,
            'M4 5h16v14H4V5zm2 2v10h12V7H6zm2 8h8l-2.5-3.2-1.8 2.2-1.3-1.5L8 15z'
        )
        : '';
    const approveButton = adminAuthenticated && wreck.public_review_status === 'pending'
        ? mapPopupIconAction(
            'map-popup-action--approve',
            t('wreck.approve'),
            `reviewWreckStatus('${wreckId}', 'approved', this)`,
            'M9 16.2 4.8 12l-1.4 1.4L9 19 21 7l-1.4-1.4L9 16.2z'
        )
        : '';
    const rejectButton = adminAuthenticated && wreck.public_review_status === 'pending'
        ? mapPopupIconAction(
            'map-popup-action--delete',
            t('wreck.reject'),
            `reviewWreckStatus('${wreckId}', 'rejected', this)`,
            'M18.3 5.7 12 12l6.3 6.3-1.4 1.4-6.3-6.3-6.3 6.3-1.4-1.4L10.6 12 4.3 5.7l1.4-1.4 6.3 6.3 6.3-6.3 1.4 1.4z'
        )
        : '';
    const deleteButton = adminAuthenticated
        ? mapPopupIconAction(
            'map-popup-action--delete',
            t('wreck.delete'),
            `deleteWreck('${wreckId}', this)`,
            'M9 3v1H4v2h16V4h-5V3H9zm-3 5l1 13a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-13H6zm4 3h1v9h-1v-9zm3 0h1v9h-1v-9z'
        )
        : '';
    return [reportButton, photoButton, reviewPhotosButton, approveButton, rejectButton, deleteButton];
}

function vehicleLoosePhotoActions(group, { includeReport = true, includeUpload = true } = {}) {
    const photos = group.photos || [];
    if (!photos.length) return [];
    const lat = Number(group.lat);
    const lon = Number(group.lon);
    const encodedPhotoIds = encodedFieldPhotoIdsForGroup(group);
    const coordinatesOk = Number.isFinite(lat) && Number.isFinite(lon) && encodedPhotoIds;
    const canCreateVehicleCase = includeReport
        && coordinatesOk
        && publicFeatureAllowed(PUBLIC_FEATURE_KEYS.manualWrecks);
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
    const reportButton = canCreateVehicleCase
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

function vehicleCasePopup(group) {
    const wreck = group.wreck;
    const lat = Number(wreck.lat);
    const lon = Number(wreck.lon);
    const years = (wreck.labels_present || []).join(', ');
    const folder = wreck.folder_url;
    const links = wreck.links || {};
    const loosePreviews = fieldPhotoGroupPreviews(group.photos);
    const fieldPreviews = [...(wreck.field_photo_previews || []), ...loosePreviews];
    const fieldPhotoTotal = Number(wreck.photo_count || 0) + group.photos.length;
    const compactLinks = [
        popupCompactLink(folder, t('wreck.openCaseShort'), t('wreck.openFolder')),
        popupCompactLink(links.street_view, 'SV', t('popup.streetView')),
        popupCompactLink(links.google_maps_satellite, 'Sat', t('popup.gmapsSat')),
        popupCompactLink(links.geoportal, 'Geoportal', t('popup.geoportal')),
    ];
    return `
        <div class="map-popup map-popup--vehicle-case">
            ${popupHeader(t('wreck.popup.title'))}
            ${popupMeta([years || '-', `${lat.toFixed(6)}, ${lon.toFixed(6)}`])}
            ${popupPhotoSection(t('wreck.popup.fieldPhotos'), fieldPreviews, { className: 'map-popup-photo-grid--field', total: fieldPhotoTotal })}
            ${popupPhotoSection(t('wreck.popup.evidencePreviews'), wreck.evidence_previews, { className: 'map-popup-photo-grid--evidence' })}
            ${popupLinks(compactLinks)}
            ${popupActions([
                ...vehicleCaseActions(wreck),
                ...vehicleLoosePhotoActions(group, { includeReport: false, includeUpload: false }),
            ])}
        </div>
    `;
}

function vehiclePhotoOnlyPopup(group) {
    const photos = group.photos || [];
    const title = photos.length > 1
        ? t('vehicle.popup.photoGroupTitle', { n: photos.length })
        : t('vehicle.popup.photoTitle');
    return `
        <div class="map-popup ${photos.length > 1 ? 'map-popup--field-photo-group' : 'map-popup--field-photo'}">
            ${popupHeader(title)}
            ${fieldPhotoGroupMeta(group, photos)}
            ${popupPhotoSection(t('wreck.popup.fieldPhotos'), fieldPhotoGroupPreviews(photos), { className: 'map-popup-photo-grid--field', total: photos.length })}
            ${fieldPhotoGroupLinks(group, photos)}
            ${popupActions(vehicleLoosePhotoActions(group))}
        </div>
    `;
}

function vehicleGroupPopup(group) {
    return group.wreck ? vehicleCasePopup(group) : vehiclePhotoOnlyPopup(group);
}

function placeVehicleMarkers() {
    clearVehicleMarkers();
    if (!vehicleLayerAllowed()) return;
    buildVehicleGroups().forEach(group => {
        const canDrag = adminAuthenticated && !group.wreck && group.photos.length > 0;
        const marker = L.marker([group.lat, group.lon], {
            icon: wreckIcon(vehicleGroupPhotoCount(group), group.wreck?.public_review_status),
            zIndexOffset: 1200,
            draggable: canDrag,
            autoPan: canDrag,
        }).addTo(map).bindPopup(vehicleGroupPopup(group), { maxWidth: group.photos.length > 1 ? 380 : 320 });
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

async function loadSavedWrecks() {
    try {
        const data = await apiJson(`${WRECKS_URL}?ts=${Date.now()}`, { cache: 'no-store' });
        if (data.status === 'ok') {
            savedWreckLayerData = data.wrecks || [];
            placeVehicleMarkers();
            updateLingeringCarsCounter();
        }
    } catch (_) {}
}

function toggleVehicleLayer(visible) {
    vehicleLayerVisible = Boolean(visible);
    placeVehicleMarkers();
}

async function deleteWreck(wreckId, button = null) {
    if (!(await ensureAdmin())) return;
    const id = safeWreckId(wreckId);
    if (!id) return;
    const confirmed = await confirmAction({
        title: t('wreck.deleteTitle'),
        message: t('wreck.deleteConfirm'),
        confirmLabel: t('wreck.delete'),
    });
    if (!confirmed) return;

    const btn = button instanceof HTMLElement ? button : null;
    if (btn) {
        btn.disabled = true;
        btn.textContent = t('wreck.deleting');
    }
    try {
        const data = await apiDeleteJson(`${WRECKS_URL}/${encodeURIComponent(id)}`);
        if (data.status !== 'ok') {
            throw new Error(data.error || t('wreck.deleteError'));
        }
        await loadSavedWrecks();
        statusEl.textContent = t('wreck.deleted');
        statusEl.className = 'ok';
    } catch (err) {
        if (btn) {
            btn.disabled = false;
            btn.textContent = t('wreck.delete');
        }
        statusEl.textContent = apiErrorMessage(err, t('wreck.deleteError'));
        statusEl.className = 'err';
    }
}

async function reviewWreckStatus(wreckId, publicReviewStatus, button = null) {
    if (!(await ensureAdmin())) return;
    const id = safeWreckId(wreckId);
    if (!id) return;
    const btn = button instanceof HTMLElement ? button : null;
    if (btn) btn.disabled = true;
    try {
        const data = await apiPatchJson(`${ADMIN_WRECKS_URL}/${encodeURIComponent(id)}/review`, {
            public_review_status: publicReviewStatus,
        });
        if (data.status !== 'ok') {
            throw new Error(data.error || t('wreck.reviewError'));
        }
        await loadSavedWrecks();
        statusEl.textContent = publicReviewStatus === 'approved' ? t('wreck.approved') : t('wreck.rejected');
        statusEl.className = 'ok';
    } catch (err) {
        statusEl.textContent = apiErrorMessage(err, t('wreck.reviewError'));
        statusEl.className = 'err';
    } finally {
        if (btn) btn.disabled = false;
    }
}
