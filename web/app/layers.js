let cadastralLayer = null;
let cadastralLayerVisible = false;

try {
    cadastralLayerVisible = localStorage.getItem(CADASTRAL_LAYER_VISIBLE_STORAGE_KEY) === '1';
} catch (err) {
    console.warn('Nie udało się odczytać ustawienia warstwy działek.', err);
}

function buildCadastralLayer() {
    return L.tileLayer.wms(CADASTRAL_WMS_URL, {
        layers: CADASTRAL_WMS_LAYERS,
        styles: 'default,default',
        format: 'image/png',
        transparent: true,
        version: '1.3.0',
        maxZoom: MAX_MAP_ZOOM,
        opacity: 0.95,
        pane: 'overlayPane',
        attribution: 'KIEG GUGiK',
    });
}

function setCadastralLayerVisible(visible) {
    cadastralLayerVisible = Boolean(visible);
    const allowed = publicLayerAllowed(PUBLIC_LAYER_KEYS.cadastral);
    const toggle = document.getElementById('toggle-cadastral-parcels');
    if (toggle) toggle.checked = cadastralLayerVisible && allowed;
    try {
        localStorage.setItem(CADASTRAL_LAYER_VISIBLE_STORAGE_KEY, cadastralLayerVisible ? '1' : '0');
    } catch (err) {
        console.warn('Nie udało się zapisać ustawienia warstwy działek.', err);
    }
    if (cadastralLayerVisible && allowed) {
        if (!cadastralLayer) cadastralLayer = buildCadastralLayer();
        if (!map.hasLayer(cadastralLayer)) cadastralLayer.addTo(map);
    } else if (cadastralLayer && map.hasLayer(cadastralLayer)) {
        map.removeLayer(cadastralLayer);
    }
}

function toggleCadastralLayer(visible) {
    setCadastralLayerVisible(visible);
}
