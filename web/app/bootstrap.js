// ─── STATE ──────────────────────────────────────
let currentWidth = 50;
let currentHeight = 50;
let lastDownload = null;   // { lat, lon, width, height } — gdzie i co ostatnio pobraliśmy
let currentJobToken = null;
let enhancementSettingsRevision = Date.now();
let settingsSaveTimer = null;
let defaultEnhancementSettings = null;

const initialMapView = readStoredMapView();
const map = L.map('map', {
    center: initialMapView.center,
    zoom: initialMapView.zoom,
    maxZoom: MAX_MAP_ZOOM,
    zoomControl: false,
    boxZoom: false,  // wyłączone — shift+drag używamy do zaznaczania
});
map.on('moveend zoomend', saveMapView);

function markerDetailMode() {
    const zoom = map.getZoom();
    if (zoom <= MARKER_DETAIL_DOT_MAX_ZOOM) return 'dots';
    if (zoom < MARKER_DETAIL_FULL_MIN_ZOOM) return 'compact';
    return 'full';
}

function updateMarkerDetailMode() {
    const container = map.getContainer();
    container.classList.remove('marker-detail--full', 'marker-detail--compact', 'marker-detail--dots');
    container.classList.add(`marker-detail--${markerDetailMode()}`);
}

map.on('zoomend', updateMarkerDetailMode);
updateMarkerDetailMode();
