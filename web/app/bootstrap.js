// ─── STATE ──────────────────────────────────────
let enhancementSettingsRevision = Date.now();
let settingsSaveTimer = null;
let defaultEnhancementSettings = null;

const initialMapView = readStoredMapView();
const map = L.map('map', {
    center: initialMapView.center,
    zoom: initialMapView.zoom,
    maxZoom: MAX_MAP_ZOOM,
    zoomControl: false,
    boxZoom: true,
});
map.on('moveend zoomend', saveMapView);

function updateMarkerDetailMode() {
    map.getContainer().classList.toggle('marker-detail--dots', map.getZoom() <= MARKER_DETAIL_DOT_MAX_ZOOM);
}

map.on('zoomend', updateMarkerDetailMode);
updateMarkerDetailMode();
