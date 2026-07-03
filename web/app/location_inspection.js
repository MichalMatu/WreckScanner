function selectedReviewCropM() {
    const cropM = parseFloat(document.getElementById('report-crop-select')?.value);
    return Number.isFinite(cropM) ? cropM : 7.5;
}

async function inspectLocationHistoryAt(latLng) {
    const inspectLat = Number(latLng?.lat);
    const inspectLon = Number(latLng?.lng);
    if (!Number.isFinite(inspectLat) || !Number.isFinite(inspectLon)) return;

    const popup = L.popup({ maxWidth: 300 })
        .setLatLng([inspectLat, inspectLon])
        .setContent(`<div style="text-align:center; padding:10px;">${t('inspect.loading')}</div>`)
        .openOn(map);

    try {
        const data = await apiPostJson('/api/inspect', {
            lat: inspectLat,
            lon: inspectLon,
            cropM: selectedReviewCropM(),
        });
        if (data.status !== 'ok' || !Array.isArray(data.crops) || data.crops.length === 0) {
            throw new Error(data.error || t('inspect.loadError'));
        }

        const cropPreviews = data.crops.map(crop => ({
            source: 'inspect',
            label: crop.year,
            public_image: crop.data_url,
            public_thumb: crop.data_url,
        }));

        popup.setContent(`
            <div class="map-popup map-popup--manual-inspect">
                ${popupHeader(t('inspect.title'))}
                ${popupMeta([t('inspect.coords', { lat: inspectLat.toFixed(6), lon: inspectLon.toFixed(6) })])}
                ${popupPhotoSection(t('inspect.evidencePreviews'), cropPreviews)}
            </div>
        `);
    } catch (err) {
        popup.setContent(`
            <div class="map-popup map-popup--manual-inspect">
                ${popupHeader(t('inspect.title'))}
                ${popupMeta([apiErrorMessage(err, t('inspect.loadError'))])}
            </div>
        `);
    }
}

async function openLocationInspectionAtContextPoint() {
    if (!contextMenuLatLng) return;
    const latLng = L.latLng(contextMenuLatLng.lat, contextMenuLatLng.lng);
    closeMapContextMenu();
    await inspectLocationHistoryAt(latLng);
}
