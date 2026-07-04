map.on('popupopen', () => {
    closeMapContextMenu();
});

const mapContextMenu = document.getElementById('map-context-menu');
const contextMenuCoords = document.getElementById('context-menu-coords');
let contextMenuLatLng = null;
let activeCadastralParcel = null;

const CADASTRAL_LAND_USE_LABEL_KEYS = {
    B: 'context.landUse.B',
    Ba: 'context.landUse.Ba',
    Bi: 'context.landUse.Bi',
    Bp: 'context.landUse.Bp',
    Bz: 'context.landUse.Bz',
    dr: 'context.landUse.dr',
    K: 'context.landUse.K',
    Ls: 'context.landUse.Ls',
    Lz: 'context.landUse.Lz',
    N: 'context.landUse.N',
    R: 'context.landUse.R',
    S: 'context.landUse.S',
    Tk: 'context.landUse.Tk',
    Ti: 'context.landUse.Ti',
    Tp: 'context.landUse.Tp',
    Tr: 'context.landUse.Tr',
    W: 'context.landUse.W',
    Wp: 'context.landUse.Wp',
    Ws: 'context.landUse.Ws',
    Ł: 'context.landUse.Laka',
    Ps: 'context.landUse.Ps',
};

function closeMapContextMenu() {
    if (!mapContextMenu || mapContextMenu.hidden) return;
    mapContextMenu.hidden = true;
    contextMenuLatLng = null;
}

function openMapContextMenu(e) {
    if (!mapContextMenu || !contextMenuCoords) return;
    if (typeof closeAppMenu === 'function') closeAppMenu();
    if (typeof cancelFieldPhotoLocationPick === 'function') cancelFieldPhotoLocationPick({ clearStatus: true });
    contextMenuLatLng = e.latlng;
    contextMenuCoords.textContent = `${contextMenuLatLng.lat.toFixed(6)}, ${contextMenuLatLng.lng.toFixed(6)}`;
    mapContextMenu.hidden = false;

    const originalEvent = e.originalEvent;
    const margin = 8;
    const menuWidth = mapContextMenu.offsetWidth || 210;
    const menuHeight = mapContextMenu.offsetHeight || 110;
    const x = Math.min(originalEvent.clientX, window.innerWidth - menuWidth - margin);
    const y = Math.min(originalEvent.clientY, window.innerHeight - menuHeight - margin);
    mapContextMenu.style.left = `${Math.max(margin, x)}px`;
    mapContextMenu.style.top = `${Math.max(margin, y)}px`;
    requestAnimationFrame(() => {
        mapContextMenu.querySelector('button:not([hidden])')?.focus({ preventScroll: true });
    });
}

function openMapSourcePanelFromContext() {
    closeMapContextMenu();
    if (typeof setAppMenuOpen === 'function') setAppMenuOpen(true);
    requestAnimationFrame(() => {
        const panel = document.getElementById('panel-map-source');
        panel?.scrollIntoView({ block: 'nearest' });
        const activeOption = panel?.querySelector('.map-source-option.is-active')
            || panel?.querySelector('.map-source-option');
        activeOption?.focus({ preventScroll: true });
    });
}

map.on('contextmenu', (e) => {
    e.originalEvent.preventDefault();
    openMapContextMenu(e);
});
document.addEventListener('click', (e) => {
    if (!mapContextMenu || mapContextMenu.hidden || mapContextMenu.contains(e.target)) return;
    closeMapContextMenu();
});
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeMapContextMenu();
});

function cadastralCodeLabel(code) {
    const sourceCode = String(code || '').trim();
    if (!sourceCode) return '';
    const labelKey = CADASTRAL_LAND_USE_LABEL_KEYS[sourceCode]
        || CADASTRAL_LAND_USE_LABEL_KEYS[sourceCode.toLowerCase()]
        || CADASTRAL_LAND_USE_LABEL_KEYS[sourceCode.toUpperCase()];
    return labelKey ? `${sourceCode} - ${t(labelKey)}` : sourceCode;
}

function cadastralParcelClipboardText(parcel = {}) {
    const primaryTerrain = cadastralCodeLabel(parcel.land_use || parcel.contour);
    const lines = [
        `${t('context.parcelTitle')}: ${parcel.parcel_number || '-'}`,
        `${t('context.parcelTerrainType')}: ${primaryTerrain || '-'}`,
        `${t('context.parcelId')}: ${parcel.parcel_id || '-'}`,
        `${t('context.parcelDistrict')}: ${parcel.district || '-'}`,
        `${t('context.parcelMunicipality')}: ${parcel.municipality || '-'}`,
        `${t('context.parcelCounty')}: ${parcel.county || '-'}`,
        `${t('context.parcelArea')}: ${parcel.area_ha ? `${parcel.area_ha} ha` : '-'}`,
        parcel.registry_group ? `${t('context.parcelRegistryGroup')}: ${parcel.registry_group}` : '',
        `${t('context.parcelPublishedAt')}: ${parcel.published_at || '-'}`,
    ];
    return lines.filter(Boolean).join('\n');
}

async function copyActiveCadastralParcel() {
    if (!activeCadastralParcel) return;
    try {
        if (!navigator.clipboard?.writeText) throw new Error('Clipboard unavailable');
        await navigator.clipboard.writeText(cadastralParcelClipboardText(activeCadastralParcel));
        statusEl.textContent = t('context.parcelCopied');
        statusEl.className = 'ok';
    } catch (_) {
        statusEl.textContent = t('context.copyError');
        statusEl.className = 'err';
    }
}

function cadastralParcelPopup(parcel = {}) {
    const terrainType = cadastralCodeLabel(parcel.land_use || parcel.contour);
    const landUse = cadastralCodeLabel(parcel.land_use);
    const contourLabel = cadastralCodeLabel(parcel.contour);
    const contour = contourLabel && contourLabel !== terrainType && contourLabel !== landUse ? contourLabel : '';
    const rows = [
        [t('context.parcelTerrainType'), terrainType],
        [t('context.parcelLandUse'), landUse],
        [t('context.parcelContour'), contour],
        [t('context.parcelNumber'), parcel.parcel_number],
        [t('context.parcelId'), parcel.parcel_id],
        [t('context.parcelDistrict'), parcel.district],
        [t('context.parcelMunicipality'), parcel.municipality],
        [t('context.parcelCounty'), parcel.county],
        [t('context.parcelVoivodeship'), parcel.voivodeship],
        [t('context.parcelArea'), parcel.area_ha ? `${parcel.area_ha} ha` : ''],
        [t('context.parcelRegistryGroup'), parcel.registry_group],
        [t('context.parcelPublishedAt'), parcel.published_at],
    ].filter(([, value]) => value);
    const rowHtml = rows.map(([label, value]) => `
        <div class="parcel-popup-row">
            <span>${escapeHtml(label)}</span>
            <strong>${escapeHtml(value)}</strong>
        </div>
    `).join('');
    const actions = popupActions([
        `<button type="button" class="map-popup-text-action" onclick="copyActiveCadastralParcel()">${escapeHtml(t('context.parcelCopyData'))}</button>`,
    ]);
    return mapPopup(`
            ${popupHeader(t('context.parcelTitle'), parcel.parcel_number || '')}
            <div class="parcel-popup-rows">${rowHtml}</div>
            ${actions}
    `, 'map-popup--parcel');
}

async function identifyCadastralParcelAtContextPoint() {
    if (!publicLayerAllowed(PUBLIC_LAYER_KEYS.cadastral) || !contextMenuLatLng) return;
    const latLng = L.latLng(contextMenuLatLng.lat, contextMenuLatLng.lng);
    closeMapContextMenu();
    activeCadastralParcel = null;
    const popup = L.popup(mapPopupOptions())
        .setLatLng(latLng)
        .setContent(mapPopup(escapeHtml(t('context.identifyingParcel')), 'map-popup--parcel'))
        .openOn(map);
    try {
        const url = `${CADASTRAL_IDENTIFY_URL}?lat=${encodeURIComponent(latLng.lat.toFixed(8))}&lon=${encodeURIComponent(latLng.lng.toFixed(8))}`;
        const data = await apiJson(url, { cache: 'no-store' });
        if (data.status !== 'ok') {
            throw new Error(data.error || t('context.parcelError'));
        }
        activeCadastralParcel = data.parcel || {};
        popup.setContent(cadastralParcelPopup(activeCadastralParcel));
    } catch (err) {
        popup.setContent(mapPopup(`
                ${popupHeader(t('context.parcelTitle'))}
                <p class="parcel-popup-hint">${escapeHtml(err.message || t('context.parcelError'))}</p>
        `, 'map-popup--parcel'));
    }
}

async function copyContextCoords() {
    if (!contextMenuLatLng) return;
    const text = `${contextMenuLatLng.lat.toFixed(6)}, ${contextMenuLatLng.lng.toFixed(6)}`;
    try {
        if (!navigator.clipboard?.writeText) throw new Error('Clipboard unavailable');
        await navigator.clipboard.writeText(text);
        statusEl.textContent = t('context.copiedCoords');
        statusEl.className = 'ok';
    } catch (_) {
        statusEl.textContent = t('context.copyError');
        statusEl.className = 'err';
    }
    closeMapContextMenu();
}

async function copyContextPlaceLink() {
    if (!contextMenuLatLng) return;
    const text = appPlaceUrl(contextMenuLatLng.lat, contextMenuLatLng.lng, map.getZoom());
    try {
        if (!navigator.clipboard?.writeText) throw new Error('Clipboard unavailable');
        await navigator.clipboard.writeText(text);
        statusEl.textContent = t('context.copiedPlaceLink');
        statusEl.className = 'ok';
    } catch (_) {
        statusEl.textContent = t('context.copyError');
        statusEl.className = 'err';
    }
    closeMapContextMenu();
}
