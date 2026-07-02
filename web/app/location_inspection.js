function selectedReviewCropM() {
    const cropM = parseFloat(document.getElementById('crop-select')?.value);
    return Number.isFinite(cropM) ? cropM : 7.5;
}

map.on('click', async (event) => {
    if (isFieldPhotoLocationPickActive()) return;
    if (!publicFeatureAllowed(PUBLIC_FEATURE_KEYS.manualWrecks)) return;

    const inspectLat = Number(event.latlng.lat);
    const inspectLon = Number(event.latlng.lng);
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
                ${popupPhotoSection(t('wreck.popup.evidencePreviews'), cropPreviews)}
                ${popupActions([`<button type="button" class="map-popup-text-action" onclick="saveManualWreck(${inspectLat.toFixed(8)}, ${inspectLon.toFixed(8)}, this)">${t('inspect.saveWreck')}</button>`])}
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
});
