// Live coordinates
const latVal = document.getElementById('lat-val');
const lonVal = document.getElementById('lon-val');

function updateCoords() {
    const c = map.getCenter();
    latVal.textContent = c.lat.toFixed(6);
    lonVal.textContent = c.lng.toFixed(6);
}
map.on('move', updateCoords);
updateCoords();

// Square area slider
const widthSlider = document.getElementById('width-slider');
const heightSlider = document.getElementById('height-slider');
const widthDisplay = document.getElementById('width-display');
const heightDisplay = document.getElementById('height-display');
const sizeLabel = document.getElementById('size-label');
const crosshair = document.getElementById('crosshair');

function clampScanSize(value) {
    const numericValue = Number.isFinite(Number(value)) ? Number(value) : SCAN_AREA_MIN_M;
    const snapped = Math.round(numericValue / SCAN_AREA_STEP_M) * SCAN_AREA_STEP_M;
    return Math.max(SCAN_AREA_MIN_M, Math.min(SCAN_AREA_MAX_M, snapped));
}

function configureScanAreaControls() {
    [widthSlider, heightSlider].filter(Boolean).forEach(slider => {
        slider.min = String(SCAN_AREA_MIN_M);
        slider.max = String(SCAN_AREA_MAX_M);
        slider.step = String(SCAN_AREA_STEP_M);
        slider.value = String(clampScanSize(slider.value));
    });
    widthSlider.hidden = SCAN_AREA_MIN_M === SCAN_AREA_MAX_M;
}

function onSliderChange() {
    currentWidth = clampScanSize(widthSlider.value);
    currentHeight = currentWidth;
    widthSlider.value = String(currentWidth);
    heightSlider.value = String(currentWidth);
    widthDisplay.textContent = `${currentWidth} m`;
    heightDisplay.textContent = `${currentHeight} m`;
    sizeLabel.textContent = `${currentWidth} \u00d7 ${currentWidth} m`;
    updateCrosshairSize();
}
configureScanAreaControls();
widthSlider.addEventListener('input', onSliderChange);
heightSlider.addEventListener('input', () => {
    widthSlider.value = heightSlider.value;
    onSliderChange();
});

function updateCrosshairSize() {
    const center = map.getCenter();
    const metersPerPixel = 40075016.686 * Math.cos(center.lat * Math.PI / 180) / Math.pow(2, map.getZoom() + 8);
    const viewportCap = Math.max(
        CROSSHAIR_MIN_PX,
        Math.min(window.innerWidth, window.innerHeight) * CROSSHAIR_MAX_VIEWPORT_RATIO
    );
    const pxW = Math.max(CROSSHAIR_MIN_PX, Math.min(viewportCap, currentWidth / metersPerPixel));
    const pxH = Math.max(CROSSHAIR_MIN_PX, Math.min(viewportCap, currentHeight / metersPerPixel));
    const ring = document.querySelector('#crosshair .ring');
    ring.style.width = pxW + 'px';
    ring.style.height = pxH + 'px';
}

map.on('zoom', updateCrosshairSize);
map.on('move', updateCrosshairSize);
window.addEventListener('resize', updateCrosshairSize);
updateCrosshairSize();

// Shift+drag square selection. The map point is only the center; analysis always uses a square.
let selectStart = null;
let selectRect = null;

map.on('mousedown', (e) => {
    if (!e.originalEvent.shiftKey) return;
    selectStart = e.latlng;
    map.dragging.disable();
    if (selectRect) { map.removeLayer(selectRect); selectRect = null; }
});

map.on('mousemove', (e) => {
    if (!selectStart) return;
    const bounds = squareBounds(selectStart, e.latlng);
    if (!selectRect) {
        selectRect = L.rectangle(bounds, { color: '#fbbf24', weight: 2, fillOpacity: 0.1, dashArray: '5,5' }).addTo(map);
    } else {
        selectRect.setBounds(bounds);
    }
});

map.on('mouseup', (e) => {
    if (!selectStart) return;
    map.dragging.enable();
    selectStart = null;
    if (!selectRect) return;
    const b = selectRect.getBounds();
    const center = b.getCenter();
    const { dLon: wM } = metersBetweenLatLng(b.getSouthWest(), b.getSouthEast());
    const { dLat: hM } = metersBetweenLatLng(b.getNorthWest(), b.getSouthWest());
    const snap = clampScanSize;
    const sizeM = Math.max(wM, hM);
    map.removeLayer(selectRect);
    selectRect = null;
    map.setView(center, map.getZoom());
    widthSlider.value = snap(sizeM);
    heightSlider.value = widthSlider.value;
    onSliderChange();
});
