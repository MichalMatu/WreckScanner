const mapViewControls = {
    lat: document.getElementById('admin-map-view-lat'),
    lon: document.getElementById('admin-map-view-lon'),
    zoom: document.getElementById('admin-map-view-zoom'),
};

let mapViewSettings = null;

function mapViewAdminControls() {
    return [
        document.getElementById('admin-map-view-current'),
        document.getElementById('admin-map-view-save'),
        ...Object.values(mapViewControls),
    ].filter(Boolean);
}

function normalizeMapViewSettings(settings) {
    const fallback = {
        lat: DEFAULT_MAP_VIEW.center[0],
        lon: DEFAULT_MAP_VIEW.center[1],
        zoom: DEFAULT_MAP_VIEW.zoom,
    };
    const raw = settings && typeof settings === 'object' ? settings : {};
    const lat = Number(raw.lat);
    const lon = Number(raw.lon);
    const zoom = Number(raw.zoom);
    if (
        Number.isFinite(lat) && lat >= -90 && lat <= 90 &&
        Number.isFinite(lon) && lon >= -180 && lon <= 180 &&
        Number.isFinite(zoom) && zoom >= 0 && zoom <= MAX_MAP_ZOOM
    ) {
        return {
            lat: Number(lat.toFixed(6)),
            lon: Number(lon.toFixed(6)),
            zoom: Math.round(zoom),
        };
    }
    return fallback;
}

function applyMapViewSettings(settings) {
    mapViewSettings = normalizeMapViewSettings(settings);
    if (mapViewControls.lat) mapViewControls.lat.value = mapViewSettings.lat.toFixed(6);
    if (mapViewControls.lon) mapViewControls.lon.value = mapViewSettings.lon.toFixed(6);
    if (mapViewControls.zoom) mapViewControls.zoom.value = String(mapViewSettings.zoom);
}

function mapViewFormSettings() {
    return normalizeMapViewSettings({
        lat: mapViewControls.lat?.value,
        lon: mapViewControls.lon?.value,
        zoom: mapViewControls.zoom?.value,
    });
}

function fillMapViewFromCurrentMap() {
    const center = map.getCenter();
    applyMapViewSettings({
        lat: center.lat,
        lon: center.lng,
        zoom: map.getZoom(),
    });
    const status = document.getElementById('admin-map-view-status');
    if (status) status.textContent = t('modal.adminPanel.mapStartCurrent');
}
