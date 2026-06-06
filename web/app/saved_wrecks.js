let savedWreckMarkers = [];
let savedWreckLayerData = [];
let savedWreckLayerVisible = true;

function clearSavedWreckMarkers() {
    savedWreckMarkers.forEach(m => map.removeLayer(m));
    savedWreckMarkers = [];
}

function safeWreckId(value) {
    return String(value ?? '').replace(/[^A-Za-z0-9_-]/g, '');
}

function savedWreckPopup(wreck) {
    const lat = Number(wreck.lat);
    const lon = Number(wreck.lon);
    const score = Number(wreck.best_score || 0);
    const years = (wreck.labels_present || []).join(', ');
    const wreckId = safeWreckId(wreck.id);
    const folder = wreck.folder_url;
    const links = wreck.links || {};
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
            `openWreckPhotoModal('${wreckId}')`,
            'M5 7h2.8L9.4 5h5.2l1.6 2H19c1.1 0 2 .9 2 2v10c0 1.1-.9 2-2 2H5c-1.1 0-2-.9-2-2V9c0-1.1.9-2 2-2zm7 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zm5-5h-2v2h-2v2h2v2h2v-2h2v-2h-2v-2z'
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
    const compactLinks = [
        popupCompactLink(folder, t('wreck.openCaseShort'), t('wreck.openFolder')),
        popupCompactLink(links.street_view, 'SV', t('popup.streetView')),
        popupCompactLink(links.google_maps_satellite, 'Sat', t('popup.gmapsSat')),
        popupCompactLink(links.geoportal, 'Geoportal', t('popup.geoportal')),
    ];
    return `
        <div class="map-popup map-popup--vehicle-case">
            ${popupHeader(t('wreck.popup.title'), `${(score * 100).toFixed(0)}%`)}
            ${popupMeta([years || '-', `${lat.toFixed(6)}, ${lon.toFixed(6)}`])}
            ${popupPhotoSection(t('wreck.popup.fieldPhotos'), wreck.field_photo_previews, { className: 'map-popup-photo-grid--field', total: wreck.photo_count })}
            ${popupPhotoSection(t('wreck.popup.evidencePreviews'), wreck.evidence_previews, { className: 'map-popup-photo-grid--evidence' })}
            ${popupLinks(compactLinks)}
            ${popupActions([reportButton, photoButton, reviewPhotosButton, approveButton, rejectButton, deleteButton])}
        </div>
    `;
}

function placeSavedWrecks(wrecks = savedWreckLayerData) {
    clearSavedWreckMarkers();
    if (!savedWreckLayerVisible || !publicLayerAllowed(PUBLIC_LAYER_KEYS.savedWrecks)) return;
    wrecks.forEach(wreck => {
        const lat = Number(wreck.lat);
        const lon = Number(wreck.lon);
        if (!Number.isFinite(lat) || !Number.isFinite(lon)) return;
        const marker = L.marker([lat, lon], {
            icon: wreckIcon(wreck.photo_count, wreck.public_review_status),
            zIndexOffset: 1200,
        }).addTo(map).bindPopup(savedWreckPopup(wreck));
        savedWreckMarkers.push(marker);
    });
}

async function loadSavedWrecks() {
    try {
        const data = await apiJson(`${WRECKS_URL}?ts=${Date.now()}`, { cache: 'no-store' });
        if (data.status === 'ok') {
            savedWreckLayerData = data.wrecks || [];
            placeSavedWrecks(savedWreckLayerData);
            updateLingeringCarsCounter();
        }
    } catch (_) {}
}

function toggleSavedWreckLayer(visible) {
    savedWreckLayerVisible = Boolean(visible);
    placeSavedWrecks(savedWreckLayerData);
}

async function saveWreck(rank, button = null) {
    if (!publicFeatureAllowed(PUBLIC_FEATURE_KEYS.yoloWrecks)) {
        statusEl.textContent = t('wreck.saveYoloDisabled');
        statusEl.className = 'err';
        return;
    }
    const btn = button instanceof HTMLElement ? button : null;
    if (btn) {
        btn.disabled = true;
        btn.textContent = t('wreck.saving');
    }
    try {
        const data = await apiPostJson(WRECKS_URL, { rank });
        if (data.status !== 'ok') {
            throw new Error(data.error || t('wreck.saveError'));
        }
        await loadSavedWrecks();
        const pendingReview = !adminAuthenticated && data.wreck?.public_review_status === 'pending';
        if (pendingReview) {
            addPendingSubmissionMarker({ lat: data.wreck?.lat, lon: data.wreck?.lon });
            if (btn) btn.textContent = t('wreck.submittedShort');
            statusEl.textContent = t('wreck.submittedForReview');
            statusEl.className = 'ok';
            return;
        }
        if (btn) btn.textContent = data.evidence_created ? t('wreck.savedShort') : t('wreck.alreadySavedShort');
        statusEl.textContent = data.evidence_created ? t('wreck.saved') : t('wreck.alreadySaved');
        statusEl.className = 'ok';
    } catch (err) {
        if (btn) {
            btn.disabled = false;
            btn.textContent = t('wreck.save');
        }
        statusEl.textContent = apiErrorMessage(err, t('wreck.saveError'));
        statusEl.className = 'err';
    }
}

async function saveManualWreck(lat, lon, button = null) {
    const latNumber = Number(lat);
    const lonNumber = Number(lon);
    if (!Number.isFinite(latNumber) || !Number.isFinite(lonNumber)) return;
    const cropM = selectedReviewCropM();

    const btn = button instanceof HTMLElement ? button : null;
    if (btn) {
        btn.disabled = true;
        btn.textContent = t('inspect.savingWreck');
    }
    try {
        const data = await apiPostJson(WRECKS_URL, { lat: latNumber, lon: lonNumber, cropM });
        if (data.status !== 'ok') {
            throw new Error(data.error || t('inspect.saveWreckError'));
        }
        await loadSavedWrecks();
        const created = Boolean(data.created);
        const pendingReview = !adminAuthenticated && data.wreck?.public_review_status === 'pending';
        if (pendingReview) {
            addPendingSubmissionMarker({ lat: data.wreck?.lat ?? latNumber, lon: data.wreck?.lon ?? lonNumber });
            if (btn) btn.textContent = t('wreck.submittedShort');
            statusEl.textContent = t('inspect.submittedWreck');
            statusEl.className = 'ok';
            return;
        }
        if (btn) btn.textContent = created ? t('inspect.savedWreck') : t('inspect.alreadySavedWreck');
        statusEl.textContent = created ? t('inspect.savedWreck') : t('inspect.alreadySavedWreck');
        statusEl.className = 'ok';
    } catch (err) {
        if (btn) {
            btn.disabled = false;
            btn.textContent = t('inspect.saveWreck');
        }
        statusEl.textContent = apiErrorMessage(err, t('inspect.saveWreckError'));
        statusEl.className = 'err';
    }
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
