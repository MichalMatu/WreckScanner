const surfacePane = map.createPane('surfacePane');
surfacePane.style.zIndex = 450;

let cadastralLayer = null;
let cadastralLayerVisible = false;
let surfaceLayer = null;
let surfaceLayerVisible = false;
let surfaceLayerLoadToken = 0;
let surfaceLayerReloadTimer = null;
let surfaceLayerInFlightKey = '';
let surfaceLayerLoadedKey = '';

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

function setSurfaceLayerStatus(key = '', params = {}, state = '') {
    const status = document.getElementById('surface-layer-status');
    if (!status) return;
    const text = key ? t(key, params) : '';
    status.textContent = text;
    status.title = params.error || text;
    status.classList.toggle('is-error', state === 'error');
    status.classList.toggle('is-ok', state === 'ok');
}

function surfaceBboxKey(bboxValues) {
    return bboxValues.map(value => Number(value).toFixed(5)).join(',');
}

async function fetchSurfaceGeojson(bboxKey) {
    const data = await apiJson(`${SURFACE_FEATURES_URL}?bbox=${encodeURIComponent(bboxKey)}`, { cache: 'no-store' });
    if (data.status === 'ok' && data.geojson?.type === 'FeatureCollection') {
        return data.geojson;
    }
    throw new Error(data.error || t('layers.surfaceError'));
}

function surfaceFeatureStyle(feature) {
    const kind = feature?.properties?.kind || 'surface';
    const colors = {
        road: '#f97316',
        sidewalk: '#22c55e',
        parking: '#38bdf8',
        kerb: '#f43f5e',
        surface: '#eab308',
    };
    return {
        color: colors[kind] || colors.surface,
        weight: kind === 'kerb' ? 5 : kind === 'sidewalk' ? 4 : 3,
        opacity: 0.96,
        fillOpacity: 0.18,
        lineCap: 'round',
        lineJoin: 'round',
        dashArray: kind === 'kerb' ? '3 5' : null,
        pane: 'surfacePane',
    };
}

function surfaceKnownTranslation(key) {
    const translated = t(key);
    return translated === key ? '' : translated;
}

function surfaceKindLabel(kind) {
    return surfaceKnownTranslation(`layers.surfaceKind.${kind || 'surface'}`) || String(kind || '');
}

function surfaceTagLabel(group, value) {
    const rawValue = String(value || '').trim();
    if (!rawValue) return '';
    const normalized = rawValue.toLowerCase().replace(/[^a-z0-9:_-]/g, '');
    return surfaceKnownTranslation(`layers.surface${group}.${normalized}`) || rawValue;
}

function surfacePopupRow(labelKey, value) {
    if (!value) return '';
    return `
        <div class="surface-popup-row">
            <span>${escapeHtml(t(labelKey))}</span>
            <strong>${escapeHtml(value)}</strong>
        </div>
    `;
}

function surfaceFeaturePopup(feature) {
    const props = feature?.properties || {};
    const rows = [
        surfacePopupRow('layers.surfacePopup.kind', surfaceKindLabel(props.kind)),
        surfacePopupRow('layers.surfacePopup.highway', surfaceTagLabel('Highway', props.highway)),
        surfacePopupRow('layers.surfacePopup.material', surfaceTagLabel('Material', props.surface)),
        surfacePopupRow('layers.surfacePopup.kerb', surfaceTagLabel('Kerb', props.kerb)),
        surfacePopupRow('layers.surfacePopup.source', props.source),
    ].filter(Boolean).join('');
    return `
        <div class="map-popup map-popup--surface">
            <b>${escapeHtml(t('layers.surface'))}</b>
            <div class="surface-popup-rows">${rows || escapeHtml(t('layers.surfaceEmpty'))}</div>
        </div>
    `;
}

async function loadSurfaceLayer() {
    if (!surfaceLayerVisible || !publicLayerAllowed(PUBLIC_LAYER_KEYS.surface)) return;
    const bounds = map.getBounds();
    const bboxValues = [bounds.getSouth(), bounds.getWest(), bounds.getNorth(), bounds.getEast()];
    const bboxKey = surfaceBboxKey(bboxValues);
    if (bboxKey === surfaceLayerInFlightKey || (bboxKey === surfaceLayerLoadedKey && surfaceLayer)) return;
    surfaceLayerInFlightKey = bboxKey;
    const token = ++surfaceLayerLoadToken;
    setSurfaceLayerStatus('layers.surfaceLoading');
    try {
        const geojson = await fetchSurfaceGeojson(bboxKey);
        if (token !== surfaceLayerLoadToken || !surfaceLayerVisible) return;
        if (surfaceLayer) map.removeLayer(surfaceLayer);
        const featureCount = Array.isArray(geojson.features) ? geojson.features.length : 0;
        surfaceLayerLoadedKey = bboxKey;
        if (featureCount) {
            surfaceLayer = L.geoJSON(geojson, {
                pane: 'surfacePane',
                style: surfaceFeatureStyle,
                pointToLayer: (_feature, latlng) => L.circleMarker(
                    latlng,
                    { radius: 5, pane: 'surfacePane', ...surfaceFeatureStyle(_feature) }
                ),
                onEachFeature: (feature, layer) => layer.bindPopup(surfaceFeaturePopup(feature)),
            }).addTo(map);
            surfaceLayer.bringToFront();
            setSurfaceLayerStatus('layers.surfaceLoaded', { n: featureCount, error: geojson.warning || '' }, 'ok');
        } else {
            surfaceLayer = null;
            setSurfaceLayerStatus('layers.surfaceEmpty', { error: geojson.error || '' }, 'ok');
        }
    } catch (err) {
        if (token === surfaceLayerLoadToken && surfaceLayerVisible) {
            if (surfaceLayer) {
                map.removeLayer(surfaceLayer);
                surfaceLayer = null;
            }
            setSurfaceLayerStatus('layers.surfaceLoadError', { error: err.message || '' }, 'error');
        }
        console.warn('Nie udało się pobrać warstwy nawierzchni.', err);
    } finally {
        if (surfaceLayerInFlightKey === bboxKey) surfaceLayerInFlightKey = '';
    }
}

function scheduleSurfaceLayerLoad(delayMs = 650) {
    if (!surfaceLayerVisible || !publicLayerAllowed(PUBLIC_LAYER_KEYS.surface)) return;
    if (surfaceLayerReloadTimer) clearTimeout(surfaceLayerReloadTimer);
    surfaceLayerReloadTimer = setTimeout(() => {
        surfaceLayerReloadTimer = null;
        loadSurfaceLayer();
    }, delayMs);
}

function setSurfaceLayerVisible(visible) {
    surfaceLayerVisible = Boolean(visible);
    const allowed = publicLayerAllowed(PUBLIC_LAYER_KEYS.surface);
    const toggle = document.getElementById('toggle-surface-layer');
    if (toggle) toggle.checked = surfaceLayerVisible && allowed;
    if (!surfaceLayerVisible && surfaceLayer) {
        map.removeLayer(surfaceLayer);
        surfaceLayer = null;
    }
    if (!surfaceLayerVisible || !allowed) {
        if (surfaceLayerReloadTimer) {
            clearTimeout(surfaceLayerReloadTimer);
            surfaceLayerReloadTimer = null;
        }
        surfaceLayerInFlightKey = '';
        surfaceLayerLoadedKey = '';
        surfaceLayerLoadToken += 1;
        setSurfaceLayerStatus('');
    }
    if (surfaceLayerVisible && allowed) scheduleSurfaceLayerLoad(0);
}

map.on('moveend zoomend', () => {
    if (surfaceLayerVisible && publicLayerAllowed(PUBLIC_LAYER_KEYS.surface)) scheduleSurfaceLayerLoad();
});
