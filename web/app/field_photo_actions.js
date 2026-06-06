async function rejectFieldPhotoGroup(encodedPhotoIds, button = null) {
    if (!(await ensureAdmin())) return;
    const photoIds = decodeFieldPhotoIds(encodedPhotoIds);
    if (!photoIds.length) return;
    const confirmed = await confirmAction({
        title: t('fieldPhoto.rejectTitle'),
        message: t('fieldPhoto.rejectConfirm', { n: photoIds.length }),
        confirmLabel: t('modal.photoReview.reject'),
    });
    if (!confirmed) return;

    const btn = button instanceof HTMLElement ? button : null;
    if (btn) btn.disabled = true;
    try {
        for (const id of photoIds) {
            const data = await apiPatchJson(`${ADMIN_PHOTOS_URL}/field/${encodeURIComponent(id)}/review`, {
                public_review_status: 'rejected',
                redactions: [],
            });
            if (data.status !== 'ok') {
                throw new Error(data.error || t('fieldPhoto.rejectError'));
            }
        }
        await loadFieldPhotos();
        statusEl.textContent = t('fieldPhoto.rejected', { n: photoIds.length });
        statusEl.className = 'ok';
    } catch (err) {
        if (btn) btn.disabled = false;
        statusEl.textContent = apiErrorMessage(err, t('fieldPhoto.rejectError'));
        statusEl.className = 'err';
    }
}

async function updateFieldPhotoLocation(photo, lat, lon) {
    const id = safeFieldPhotoId(photo.id);
    if (!id) throw new Error(t('fieldPhoto.locationError'));
    const data = await apiPatchJson(`${FIELD_PHOTOS_URL}/${encodeURIComponent(id)}/location`, { lat, lon });
    if (data.status !== 'ok') {
        throw new Error(data.error || t('fieldPhoto.locationError'));
    }
}

function photoIdsForGroup(group) {
    return (group.photos || []).map(photo => safeFieldPhotoId(photo.id)).filter(Boolean);
}

function nearestWreckForAttachment(lat, lon) {
    let nearest = null;
    savedWreckLayerData.forEach(wreck => {
        const wreckLat = Number(wreck.lat);
        const wreckLon = Number(wreck.lon);
        if (!Number.isFinite(wreckLat) || !Number.isFinite(wreckLon)) return;
        const distanceM = metersBetween(lat, lon, wreckLat, wreckLon);
        if (distanceM > FIELD_PHOTO_ATTACH_TO_WRECK_RADIUS_M) return;
        if (!nearest || distanceM < nearest.distanceM) nearest = { wreck, distanceM };
    });
    return nearest;
}

async function attachFieldPhotoGroupToWreck(group, wreck) {
    const photoIds = photoIdsForGroup(group);
    const wreckId = safeWreckId(wreck.id);
    if (!photoIds.length || !wreckId) return;
    const data = await apiPostJson(`${WRECKS_URL}/${encodeURIComponent(wreckId)}/field-photos/attach`, {
        photo_ids: photoIds,
    });
    if (data.status !== 'ok') {
        throw new Error(data.error || t('fieldPhoto.attachToWreckError'));
    }
}

function decodeFieldPhotoIds(encodedPhotoIds) {
    try {
        const ids = JSON.parse(decodeURIComponent(String(encodedPhotoIds || '[]')));
        return Array.isArray(ids) ? ids.map(safeFieldPhotoId).filter(Boolean) : [];
    } catch (_) {
        return [];
    }
}

function fieldPhotosForReport(encodedPhotoIds) {
    const photoIds = new Set(decodeFieldPhotoIds(encodedPhotoIds));
    if (!photoIds.size) return [];
    return fieldPhotoLayerData
        .filter(photo =>
            photoIds.has(safeFieldPhotoId(photo.id))
            && fieldPhotoIssueType(photo) === FIELD_PHOTO_ISSUE_TYPE_VEHICLE
            && fieldPhotoReviewStatus(photo) === 'approved'
        )
        .map(photo => {
            const id = safeFieldPhotoId(photo.id);
            return {
                id,
                url: photo.public_image || photo.public_thumb,
                filename: `zdjecie_terenowe_${id}.jpg`,
            };
        })
        .filter(photo => photo.id && photo.url)
        .slice(0, REPORT_PHOTO_MAX_COUNT);
}

async function createManualWreckForFieldPhotoGroup(lat, lon) {
    if (!publicFeatureAllowed(PUBLIC_FEATURE_KEYS.manualWrecks)) return null;
    const latNumber = Number(lat);
    const lonNumber = Number(lon);
    if (!Number.isFinite(latNumber) || !Number.isFinite(lonNumber)) {
        throw new Error(t('fieldPhoto.prepareCaseError'));
    }

    const saveData = await apiPostJson(WRECKS_URL, { lat: latNumber, lon: lonNumber });
    if (saveData.status !== 'ok') {
        throw new Error(saveData.error || t('fieldPhoto.prepareCaseError'));
    }
    const wreckId = safeWreckId(saveData.wreck?.id);
    if (!wreckId) throw new Error(t('fieldPhoto.prepareCaseError'));
    await loadSavedWrecks();
    return wreckId;
}

async function createWreckForFieldPhotoGroup(lat, lon, encodedPhotoIds) {
    if (!(await ensureAdmin())) return null;
    const latNumber = Number(lat);
    const lonNumber = Number(lon);
    const photoIds = decodeFieldPhotoIds(encodedPhotoIds);
    if (!Number.isFinite(latNumber) || !Number.isFinite(lonNumber) || !photoIds.length) {
        throw new Error(t('fieldPhoto.prepareCaseError'));
    }

    const saveData = await apiPostJson(WRECKS_URL, { lat: latNumber, lon: lonNumber });
    if (saveData.status !== 'ok') {
        throw new Error(saveData.error || t('fieldPhoto.prepareCaseError'));
    }
    const wreckId = safeWreckId(saveData.wreck?.id);
    if (!wreckId) throw new Error(t('fieldPhoto.prepareCaseError'));

    const attachData = await apiPostJson(`${WRECKS_URL}/${encodeURIComponent(wreckId)}/field-photos/attach`, {
        photo_ids: photoIds,
    });
    if (attachData.status !== 'ok') {
        throw new Error(attachData.error || t('fieldPhoto.attachToWreckError'));
    }

    await loadSavedWrecks();
    await loadFieldPhotos();
    return wreckId;
}

async function openFieldPhotoGroupReport(lat, lon, encodedPhotoIds, button = null) {
    if (!publicFeatureAllowed(PUBLIC_FEATURE_KEYS.manualWrecks)) return;
    const btn = button instanceof HTMLElement ? button : null;
    if (btn) btn.disabled = true;
    statusEl.textContent = t('fieldPhoto.prepareCaseSaving');
    statusEl.className = '';
    try {
        if (typeof refreshAdminStatus === 'function') await refreshAdminStatus();
        const wreckId = adminAuthenticated
            ? await createWreckForFieldPhotoGroup(lat, lon, encodedPhotoIds)
            : await createManualWreckForFieldPhotoGroup(lat, lon);
        if (!wreckId) return;
        statusEl.textContent = t('fieldPhoto.prepareCaseSaved');
        statusEl.className = 'ok';
        openReportPackageModal(wreckId, { extraPhotos: adminAuthenticated ? [] : fieldPhotosForReport(encodedPhotoIds) });
    } catch (err) {
        statusEl.textContent = apiErrorMessage(err, t('fieldPhoto.prepareCaseError'));
        statusEl.className = 'err';
    } finally {
        if (btn) btn.disabled = false;
    }
}

async function openFieldPhotoGroupPhotoUpload(lat, lon, encodedPhotoIds, issueType = FIELD_PHOTO_ISSUE_TYPE_VEHICLE, button = null) {
    if (!publicFeatureAllowed(PUBLIC_FEATURE_KEYS.photoUploads)) return;
    const latNumber = Number(lat);
    const lonNumber = Number(lon);
    const safeIssueType = FIELD_PHOTO_ISSUE_TYPES.has(issueType) ? issueType : FIELD_PHOTO_ISSUE_TYPE_VEHICLE;
    if (!Number.isFinite(latNumber) || !Number.isFinite(lonNumber) || !decodeFieldPhotoIds(encodedPhotoIds).length) return;
    if (!fieldPhotoIssueAllowed(safeIssueType)) {
        statusEl.textContent = t('modal.fieldPhoto.issueTypeUnavailable');
        statusEl.className = 'err';
        return;
    }
    const btn = button instanceof HTMLElement ? button : null;
    if (btn) btn.disabled = true;
    try {
        await openFieldPhotoUploadModal({
            fallbackLatLng: L.latLng(latNumber, lonNumber),
            ignoreExifGps: true,
            issueType: safeIssueType,
        });
    } catch (err) {
        statusEl.textContent = err.message || t('fieldPhoto.saveError');
        statusEl.className = 'err';
    } finally {
        if (btn) btn.disabled = false;
    }
}

async function updateFieldPhotoGroupLocation(group, marker) {
    if (!adminAuthenticated) {
        await loadFieldPhotos();
        return;
    }
    const latlng = marker.getLatLng();
    const photos = (group.photos || []).filter(photo => safeFieldPhotoId(photo.id));
    if (!photos.length) {
        await loadFieldPhotos();
        return;
    }

    const nearWreck = group.issueType === FIELD_PHOTO_ISSUE_TYPE_VEHICLE
        ? nearestWreckForAttachment(latlng.lat, latlng.lng)
        : null;
    if (nearWreck) {
        marker.dragging?.disable();
        statusEl.textContent = t('fieldPhoto.attachToWreckSaving', { n: photos.length });
        statusEl.className = '';
        try {
            await attachFieldPhotoGroupToWreck(group, nearWreck.wreck);
            statusEl.textContent = t('fieldPhoto.attachToWreckSaved', { n: photos.length });
            statusEl.className = 'ok';
        } catch (err) {
            statusEl.textContent = apiErrorMessage(err, t('fieldPhoto.attachToWreckError'));
            statusEl.className = 'err';
        } finally {
            await loadSavedWrecks();
            await loadFieldPhotos();
        }
        return;
    }

    marker.dragging?.disable();
    statusEl.textContent = t('fieldPhoto.locationSaving', { n: photos.length });
    statusEl.className = '';
    try {
        for (const photo of photos) {
            await updateFieldPhotoLocation(photo, latlng.lat, latlng.lng);
        }
        statusEl.textContent = t('fieldPhoto.locationUpdated', { n: photos.length });
        statusEl.className = 'ok';
    } catch (err) {
        statusEl.textContent = apiErrorMessage(err, t('fieldPhoto.locationError'));
        statusEl.className = 'err';
    } finally {
        await loadFieldPhotos();
    }
}

async function deleteFieldPhotoGroup(encodedPhotoIds, button = null) {
    if (!(await ensureAdmin())) return;
    const photoIds = decodeFieldPhotoIds(encodedPhotoIds);
    if (!photoIds.length) return;
    const confirmed = await confirmAction({
        title: t('fieldPhoto.deleteTitle'),
        message: t('fieldPhoto.deleteConfirm', { n: photoIds.length }),
        confirmLabel: t('fieldPhoto.delete'),
    });
    if (!confirmed) return;

    const btn = button instanceof HTMLElement ? button : null;
    if (btn) {
        btn.disabled = true;
    }
    try {
        for (const id of photoIds) {
            const data = await apiDeleteJson(`${FIELD_PHOTOS_URL}/${encodeURIComponent(id)}`);
            if (data.status !== 'ok') {
                throw new Error(data.error || t('fieldPhoto.deleteError'));
            }
        }
        await loadFieldPhotos();
        statusEl.textContent = t('fieldPhoto.deleted', { n: photoIds.length });
        statusEl.className = 'ok';
    } catch (err) {
        if (btn) btn.disabled = false;
        statusEl.textContent = apiErrorMessage(err, t('fieldPhoto.deleteError'));
        statusEl.className = 'err';
    }
}
