map.on('popupopen', () => {
    closeMapContextMenu();
});

const mapContextMenu = document.getElementById('map-context-menu');
const contextMenuCoordsValue = document.getElementById('context-menu-coords-value');
let contextMenuLatLng = null;
let activeCadastralParcel = null;
let activeReverseAddress = null;
let mapContextReturnFocus = null;

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

function mapContextMenuItems() {
    if (!mapContextMenu) return [];
    return Array.from(mapContextMenu.querySelectorAll('[role="menuitem"]'))
        .filter(item => !item.hidden && !item.disabled);
}

function focusMapContextMenuItem(index = 0) {
    const items = mapContextMenuItems();
    if (!items.length) return;
    const nextIndex = (index + items.length) % items.length;
    items.forEach((item, itemIndex) => { item.tabIndex = itemIndex === nextIndex ? 0 : -1; });
    items[nextIndex].focus({ preventScroll: true });
}

function closeMapContextMenu({ restoreFocus = true } = {}) {
    if (!mapContextMenu || mapContextMenu.hidden) return;
    mapContextMenu.hidden = true;
    contextMenuLatLng = null;
    mapContextMenuItems().forEach(item => { item.tabIndex = -1; });
    const returnFocus = mapContextReturnFocus;
    mapContextReturnFocus = null;
    if (restoreFocus && returnFocus?.isConnected) returnFocus.focus({ preventScroll: true });
}

function openMapContextMenu(e) {
    if (!mapContextMenu || !contextMenuCoordsValue) return;
    if (typeof closeAppMenu === 'function') closeAppMenu();
    if (typeof cancelFieldPhotoLocationPick === 'function') cancelFieldPhotoLocationPick({ clearStatus: true });
    contextMenuLatLng = e.latlng;
    mapContextReturnFocus = document.activeElement instanceof HTMLElement
        ? document.activeElement
        : map.getContainer();
    contextMenuCoordsValue.textContent = `${contextMenuLatLng.lat.toFixed(6)}, ${contextMenuLatLng.lng.toFixed(6)}`;
    mapContextMenu.hidden = false;

    const originalEvent = e.originalEvent || {};
    const mapRect = map.getContainer().getBoundingClientRect();
    const mapPoint = map.latLngToContainerPoint(contextMenuLatLng);
    const margin = 8;
    const menuWidth = mapContextMenu.offsetWidth || 210;
    const menuHeight = mapContextMenu.offsetHeight || 110;
    const clientX = Number.isFinite(originalEvent.clientX) ? originalEvent.clientX : mapRect.left + mapPoint.x;
    const clientY = Number.isFinite(originalEvent.clientY) ? originalEvent.clientY : mapRect.top + mapPoint.y;
    const x = Math.min(clientX, window.innerWidth - menuWidth - margin);
    const y = Math.min(clientY, window.innerHeight - menuHeight - margin);
    mapContextMenu.style.left = `${Math.max(margin, x)}px`;
    mapContextMenu.style.top = `${Math.max(margin, y)}px`;
    requestAnimationFrame(() => focusMapContextMenuItem(0));
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

map.getContainer().addEventListener('keydown', event => {
    if (!(event.key === 'ContextMenu' || (event.shiftKey && event.key === 'F10'))) return;
    event.preventDefault();
    event.stopPropagation();
    openMapContextMenu({
        latlng: map.getCenter(),
        originalEvent: null,
    });
});

mapContextMenu?.addEventListener('keydown', event => {
    const items = mapContextMenuItems();
    const activeIndex = items.indexOf(document.activeElement);
    let nextIndex = null;
    if (event.key === 'ArrowDown' || event.key === 'ArrowRight') nextIndex = activeIndex + 1;
    else if (event.key === 'ArrowUp' || event.key === 'ArrowLeft') nextIndex = activeIndex - 1;
    else if (event.key === 'Home') nextIndex = 0;
    else if (event.key === 'End') nextIndex = items.length - 1;
    else if (event.key === 'Tab') {
        closeMapContextMenu({ restoreFocus: false });
        return;
    }
    if (nextIndex === null) return;
    event.preventDefault();
    event.stopPropagation();
    focusMapContextMenuItem(nextIndex);
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

function reverseAddressClipboardText(address = {}) {
    const lines = [
        `${t('context.addressTitle')}: ${address.formatted || '-'}`,
        address.display_name ? `${t('context.addressFull')}: ${address.display_name}` : '',
        Number.isFinite(Number(address.distance_m)) ? `${t('context.addressDistance')}: ${address.distance_m} m` : '',
    ];
    return lines.filter(Boolean).join('\n');
}

async function copyActiveReverseAddress() {
    if (!activeReverseAddress) return;
    try {
        if (!navigator.clipboard?.writeText) throw new Error('Clipboard unavailable');
        await navigator.clipboard.writeText(reverseAddressClipboardText(activeReverseAddress));
        statusEl.textContent = t('context.addressCopied');
        statusEl.className = 'ok';
    } catch (_) {
        statusEl.textContent = t('context.copyError');
        statusEl.className = 'err';
    }
}

function reverseAddressPopup(address = {}) {
    const rows = [
        [t('context.addressStreet'), [address.road, address.house_number].filter(Boolean).join(' ')],
        [t('context.addressDistrict'), address.district],
        [t('context.addressCity'), [address.postcode, address.city].filter(Boolean).join(' ')],
        [t('context.addressSource'), address.source_label || address.source],
        [t('context.addressDistance'), Number.isFinite(Number(address.distance_m)) ? `${address.distance_m} m` : ''],
    ].filter(([, value]) => value);
    const rowHtml = rows.map(([label, value]) => `
        <div class="parcel-popup-row">
            <span>${escapeHtml(label)}</span>
            <strong>${escapeHtml(value)}</strong>
        </div>
    `).join('');
    const actions = popupActions([
        `<button type="button" class="map-popup-text-action" onclick="copyActiveReverseAddress()">${escapeHtml(t('context.addressCopyData'))}</button>`,
    ]);
    return mapPopup(`
            ${popupHeader(t('context.addressTitle'), address.formatted || '')}
            <div class="parcel-popup-rows">${rowHtml}</div>
            ${actions}
    `, 'map-popup--address');
}

async function showAddressAtContextPoint() {
    if (!contextMenuLatLng) return;
    const latLng = L.latLng(contextMenuLatLng.lat, contextMenuLatLng.lng);
    closeMapContextMenu();
    activeReverseAddress = null;
    const popup = L.popup(mapPopupOptions())
        .setLatLng(latLng)
        .setContent(mapPopup(escapeHtml(t('context.addressLoading')), 'map-popup--address'))
        .openOn(map);
    try {
        const url = `${ADDRESS_REVERSE_URL}?lat=${encodeURIComponent(latLng.lat.toFixed(8))}&lon=${encodeURIComponent(latLng.lng.toFixed(8))}`;
        const data = await apiJson(url, { cache: 'no-store' });
        if (data.status !== 'ok') {
            throw new Error(data.error || t('context.addressError'));
        }
        activeReverseAddress = {
            ...(data.address || {}),
            query_lat: latLng.lat.toFixed(6),
            query_lon: latLng.lng.toFixed(6),
        };
        popup.setContent(reverseAddressPopup(activeReverseAddress));
    } catch (err) {
        popup.setContent(mapPopup(`
                ${popupHeader(t('context.addressTitle'))}
                <p class="parcel-popup-hint">${escapeHtml(err.message || t('context.addressError'))}</p>
        `, 'map-popup--address'));
    }
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
