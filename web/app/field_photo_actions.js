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

function decodeFieldPhotoIds(encodedPhotoIds) {
    try {
        const ids = JSON.parse(decodeURIComponent(String(encodedPhotoIds || '[]')));
        return Array.isArray(ids) ? ids.map(safeFieldPhotoId).filter(Boolean) : [];
    } catch (_) {
        return [];
    }
}

async function openFieldPhotoGroupReport(lat, lon, encodedPhotoIds, button = null) {
    if (!publicFeatureAllowed(PUBLIC_FEATURE_KEYS.reportPdfs)) return;
    const btn = button instanceof HTMLElement ? button : null;
    if (btn) btn.disabled = true;
    statusEl.textContent = '';
    statusEl.className = '';
    try {
        const photoIds = decodeFieldPhotoIds(encodedPhotoIds);
        await openFieldPhotoReportPdfModal(lat, lon, photoIds);
    } catch (err) {
        statusEl.textContent = apiErrorMessage(err, t('modal.report.generateError'));
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
            mapLatLng: L.latLng(latNumber, lonNumber),
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

function normalizeFieldPhotoVehicleResolutionStatus(status) {
    const safeStatus = String(status || FIELD_PHOTO_VEHICLE_RESOLUTION_STATUS_ACTIVE).trim();
    return FIELD_PHOTO_VEHICLE_RESOLUTION_STATUSES.has(safeStatus)
        ? safeStatus
        : FIELD_PHOTO_VEHICLE_RESOLUTION_STATUS_ACTIVE;
}

async function updateFieldPhotoGroupResolution(encodedPhotoIds, status, button = null) {
    if (!(await ensureAdmin())) return;
    const photoIds = decodeFieldPhotoIds(encodedPhotoIds);
    if (!photoIds.length) return;
    const safeStatus = normalizeFieldPhotoVehicleResolutionStatus(status);
    const removing = safeStatus === FIELD_PHOTO_VEHICLE_RESOLUTION_STATUS_REMOVED;
    const confirmed = await confirmAction({
        title: t(removing ? 'fieldPhoto.markRemovedTitle' : 'fieldPhoto.markActiveTitle'),
        message: t(removing ? 'fieldPhoto.markRemovedConfirm' : 'fieldPhoto.markActiveConfirm', { n: photoIds.length }),
        confirmLabel: t(removing ? 'fieldPhoto.markRemoved' : 'fieldPhoto.markActive'),
    });
    if (!confirmed) return;

    const btn = button instanceof HTMLElement ? button : null;
    if (btn) btn.disabled = true;
    try {
        const data = await apiPatchJson(`${ADMIN_PHOTOS_URL}/field/${encodeURIComponent(photoIds[0])}/review`, {
            vehicle_resolution_status: safeStatus,
        });
        if (data.status !== 'ok') {
            throw new Error(data.error || t('fieldPhoto.resolutionError'));
        }
        await loadFieldPhotos();
        const updatedCount = Array.isArray(data.vehicle_resolution_updated_photo_ids)
            ? data.vehicle_resolution_updated_photo_ids.length
            : photoIds.length;
        statusEl.textContent = t(removing ? 'fieldPhoto.markedRemoved' : 'fieldPhoto.markedActive', {
            n: updatedCount,
        });
        statusEl.className = 'ok';
    } catch (err) {
        if (btn) btn.disabled = false;
        statusEl.textContent = apiErrorMessage(err, t('fieldPhoto.resolutionError'));
        statusEl.className = 'err';
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
