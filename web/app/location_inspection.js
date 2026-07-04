const INSPECT_LOCATION_MAX_ATTEMPTS = 2;
const INSPECT_LOCATION_RETRY_DELAY_MS = 700;

function selectedReviewCropM() {
    const cropM = parseFloat(document.getElementById('report-crop-select')?.value);
    return Number.isFinite(cropM) ? cropM : 7.5;
}

function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

function normalizedInspectYears(years) {
    return Array.isArray(years)
        ? years.map(year => String(year || '').trim()).filter(Boolean)
        : [];
}

function mergeInspectCrops(cropsByYear, crops) {
    (Array.isArray(crops) ? crops : []).forEach(crop => {
        const year = String(crop?.year || '').trim();
        if (!year || !crop?.data_url) return;
        cropsByYear.set(year, crop);
    });
}

function sortedInspectCrops(cropsByYear, expectedYears) {
    const order = new Map(expectedYears.map((year, index) => [year, index]));
    return Array.from(cropsByYear.entries())
        .sort(([yearA], [yearB]) => {
            const orderA = order.has(yearA) ? order.get(yearA) : Number.MAX_SAFE_INTEGER;
            const orderB = order.has(yearB) ? order.get(yearB) : Number.MAX_SAFE_INTEGER;
            if (orderA !== orderB) return orderA - orderB;
            const numericA = Number(yearA);
            const numericB = Number(yearB);
            if (Number.isFinite(numericA) && Number.isFinite(numericB)) return numericA - numericB;
            return yearA.localeCompare(yearB);
        })
        .map(([, crop]) => crop);
}

async function fetchLocationHistoryCrops(lat, lon, cropM) {
    const cropsByYear = new Map();
    let expectedYears = [];
    let lastData = null;
    let lastError = null;

    for (let attempt = 0; attempt < INSPECT_LOCATION_MAX_ATTEMPTS; attempt += 1) {
        try {
            const data = await apiPostJson('/api/inspect', { lat, lon, cropM });
            lastData = data;
            if (data.status !== 'ok' || !Array.isArray(data.crops)) {
                throw new Error(data.error || t('inspect.loadError'));
            }

            const responseExpectedYears = normalizedInspectYears(data.expected_years);
            if (responseExpectedYears.length) expectedYears = responseExpectedYears;
            mergeInspectCrops(cropsByYear, data.crops);

            const responseMissingYears = normalizedInspectYears(data.missing_years);
            const missingYears = expectedYears.length
                ? expectedYears.filter(year => !cropsByYear.has(year))
                : responseMissingYears.filter(year => !cropsByYear.has(year));
            if (cropsByYear.size > 0 && missingYears.length === 0) break;
        } catch (err) {
            lastError = err;
            if (attempt === INSPECT_LOCATION_MAX_ATTEMPTS - 1 && cropsByYear.size === 0) {
                throw err;
            }
        }

        if (attempt < INSPECT_LOCATION_MAX_ATTEMPTS - 1) {
            await delay(INSPECT_LOCATION_RETRY_DELAY_MS * (attempt + 1));
        }
    }

    const crops = sortedInspectCrops(cropsByYear, expectedYears);
    if (!crops.length) {
        throw new Error(lastData?.error || lastError?.message || t('inspect.loadError'));
    }
    return crops;
}

async function inspectLocationHistoryAt(latLng) {
    const inspectLat = Number(latLng?.lat);
    const inspectLon = Number(latLng?.lng);
    if (!Number.isFinite(inspectLat) || !Number.isFinite(inspectLon)) return;

    const popup = L.popup({ maxWidth: 380 })
        .setLatLng([inspectLat, inspectLon])
        .setContent(`<div style="text-align:center; padding:10px;">${t('inspect.loading')}</div>`)
        .openOn(map);

    try {
        const crops = await fetchLocationHistoryCrops(inspectLat, inspectLon, selectedReviewCropM());
        const cropPreviews = crops.map(crop => ({
            source: 'inspect',
            label: crop.year,
            public_image: crop.data_url,
            public_thumb: crop.data_url,
        }));

        popup.setContent(`
            <div class="map-popup map-popup--manual-inspect">
                ${popupHeader(t('inspect.title'))}
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
