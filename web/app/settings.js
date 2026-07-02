// Ustawienia filtra są zapisywane na backendzie, żeby mapa używała
// tych samych parametrów na wszystkich urządzeniach.
const enhancementControls = {
    enabled: document.getElementById('enhancement-enabled'),
    clahe: document.getElementById('enhancement-clahe'),
    tile: document.getElementById('enhancement-tile'),
    pLow: document.getElementById('enhancement-p-low'),
    pHigh: document.getElementById('enhancement-p-high'),
    outLow: document.getElementById('enhancement-out-low'),
    outHigh: document.getElementById('enhancement-out-high'),
    decast: document.getElementById('enhancement-decast'),
};

const enhancementControlFields = {
    clahe: 'clahe_clip_limit',
    tile: 'clahe_tile_grid_size',
    pLow: 'l_percentile_low',
    pHigh: 'l_percentile_high',
    outLow: 'l_output_low',
    outHigh: 'l_output_high',
    decast: 'decast_strength',
};

const publicLayerControls = {
    [PUBLIC_LAYER_KEYS.savedWrecks]: document.getElementById('admin-layer-saved-wrecks'),
    [PUBLIC_LAYER_KEYS.fieldPhotoVehicle]: document.getElementById('admin-layer-field-photo-vehicle'),
    [PUBLIC_LAYER_KEYS.fieldPhotoInfrastructure]: document.getElementById('admin-layer-field-photo-infrastructure'),
    [PUBLIC_LAYER_KEYS.fieldPhotoSmoke]: document.getElementById('admin-layer-field-photo-smoke'),
    [PUBLIC_LAYER_KEYS.fieldPhotoPending]: document.getElementById('admin-layer-field-photo-pending'),
    [PUBLIC_LAYER_KEYS.cadastral]: document.getElementById('admin-layer-cadastral'),
    [PUBLIC_LAYER_KEYS.surface]: document.getElementById('admin-layer-surface'),
    [PUBLIC_LAYER_KEYS.baseMapOsm]: document.getElementById('admin-layer-base-map-osm'),
};
const publicFeatureControls = {
    [PUBLIC_FEATURE_KEYS.manualWrecks]: document.getElementById('admin-feature-manual-wrecks'),
    [PUBLIC_FEATURE_KEYS.photoUploads]: document.getElementById('admin-feature-photo-uploads'),
};
const publicLayerToggleRows = {
    [PUBLIC_LAYER_KEYS.savedWrecks]: document.getElementById('toggle-saved-wrecks')?.closest('.layer-toggle'),
    [PUBLIC_LAYER_KEYS.fieldPhotoVehicle]: document.getElementById('toggle-field-photo-vehicle')?.closest('.layer-toggle'),
    [PUBLIC_LAYER_KEYS.fieldPhotoInfrastructure]: document.getElementById('toggle-field-photo-infrastructure')?.closest('.layer-toggle'),
    [PUBLIC_LAYER_KEYS.fieldPhotoSmoke]: document.getElementById('toggle-field-photo-smoke')?.closest('.layer-toggle'),
    [PUBLIC_LAYER_KEYS.fieldPhotoPending]: document.getElementById('toggle-field-photo-pending')?.closest('.layer-toggle'),
    [PUBLIC_LAYER_KEYS.cadastral]: document.getElementById('toggle-cadastral-parcels')?.closest('.layer-toggle'),
    [PUBLIC_LAYER_KEYS.surface]: document.getElementById('toggle-surface-layer')?.closest('.layer-toggle'),
};
const adminSettingsControls = [
    document.getElementById('crop-select'),
    document.getElementById('enhancement-reset'),
    document.getElementById('photo-retention-refresh'),
    document.getElementById('photo-retention-dry-run'),
    document.getElementById('photo-retention-apply'),
    document.getElementById('admin-public-layers-save'),
    document.getElementById('admin-public-features-save'),
    ...Object.values(publicLayerControls),
    ...Object.values(publicFeatureControls),
    ...Object.values(enhancementControls),
].filter(Boolean);
let publicLayerSettings = Object.fromEntries(Object.values(PUBLIC_LAYER_KEYS).map(key => [key, true]));
let publicFeatureSettings = Object.fromEntries(Object.values(PUBLIC_FEATURE_KEYS).map(key => [key, true]));
let publicLayerSettingsLoaded = false;
let publicFeatureSettingsLoaded = false;
let fieldPhotoIssueFilters = Object.fromEntries(Array.from(FIELD_PHOTO_ISSUE_TYPES, issueType => [issueType, true]));
let pendingFieldPhotoLayerVisible = true;

function updateSettingsAccess() {
    const locked = !adminAuthenticated;
    const settingsModal = document.getElementById('modal-settings');
    const lockHint = document.getElementById('settings-lock-hint');
    settingsModal?.classList.toggle('settings-locked', locked);
    if (lockHint) lockHint.hidden = !locked;
    adminSettingsControls.forEach(control => { control.disabled = locked; });
    updatePublicLayerAccess();
    updatePublicFeatureAccess();
}

function normalizePublicLayerSettings(settings) {
    const normalized = Object.fromEntries(Object.values(PUBLIC_LAYER_KEYS).map(key => [key, true]));
    if (!settings || typeof settings !== 'object') return normalized;
    Object.keys(normalized).forEach(key => {
        if (key in settings) normalized[key] = Boolean(settings[key]);
    });
    return normalized;
}

function fieldPhotoPublicLayerKey(issueType) {
    const safeIssueType = FIELD_PHOTO_ISSUE_TYPES.has(issueType) ? issueType : FIELD_PHOTO_ISSUE_TYPE_VEHICLE;
    return FIELD_PHOTO_PUBLIC_LAYER_KEYS[safeIssueType] || PUBLIC_LAYER_KEYS.fieldPhotoVehicle;
}

function publicLayerAllowed(layerKey) {
    if (adminAuthenticated) return true;
    if (!publicLayerSettingsLoaded) return false;
    return publicLayerSettings[layerKey] !== false;
}

function normalizePublicFeatureSettings(settings) {
    const normalized = Object.fromEntries(Object.values(PUBLIC_FEATURE_KEYS).map(key => [key, true]));
    if (!settings || typeof settings !== 'object') return normalized;
    Object.keys(normalized).forEach(key => {
        if (key in settings) normalized[key] = Boolean(settings[key]);
    });
    return normalized;
}

function publicFeatureAllowed(featureKey) {
    if (adminAuthenticated) return true;
    if (!publicFeatureSettingsLoaded) return false;
    return publicFeatureSettings[featureKey] !== false;
}

function publicLayerFormSettings() {
    const settings = {};
    Object.entries(publicLayerControls).forEach(([key, control]) => {
        settings[key] = control ? Boolean(control.checked) : publicLayerSettings[key] !== false;
    });
    return normalizePublicLayerSettings(settings);
}

function publicFeatureFormSettings() {
    const settings = {};
    Object.entries(publicFeatureControls).forEach(([key, control]) => {
        settings[key] = control ? Boolean(control.checked) : publicFeatureSettings[key] !== false;
    });
    return normalizePublicFeatureSettings(settings);
}

function updateAdminPublicLayerControls() {
    Object.entries(publicLayerControls).forEach(([key, control]) => {
        if (!control) return;
        control.checked = publicLayerSettings[key] !== false;
        control.disabled = !adminAuthenticated;
    });
}

function updateAdminPublicFeatureControls() {
    Object.entries(publicFeatureControls).forEach(([key, control]) => {
        if (!control) return;
        control.checked = publicFeatureSettings[key] !== false;
        control.disabled = !adminAuthenticated;
    });
}

function updatePublicLayerControlVisibility() {
    Object.entries(publicLayerToggleRows).forEach(([key, row]) => {
        if (!row) return;
        const allowed = publicLayerAllowed(key);
        row.hidden = !allowed;
        const input = row.querySelector('input');
        if (input) {
            input.disabled = !allowed;
        }
    });
    const contextIdentifyParcelButton = document.getElementById('context-identify-parcel');
    if (contextIdentifyParcelButton) {
        contextIdentifyParcelButton.hidden = !publicLayerAllowed(PUBLIC_LAYER_KEYS.cadastral);
    }
    document.getElementById('map-layer-controls')?.classList.toggle(
        'is-loading-public-layers',
        !publicLayerSettingsLoaded && !adminAuthenticated
    );
}

function updatePublicLayerAccess() {
    updateAdminPublicLayerControls();
    updatePublicLayerControlVisibility();
    updateFieldPhotoIssueOptions();
    updatePublicFeatureControlVisibility();
}

function updatePublicFeatureControlVisibility() {
    const photoUploadsAllowed = publicFeatureAllowed(PUBLIC_FEATURE_KEYS.photoUploads);
    const contextFieldPhotoButton = document.getElementById('context-add-field-photos');
    const fieldPhotoUploadAvailable = photoUploadsAllowed && fieldPhotoAnyIssueAllowed();
    if (contextFieldPhotoButton) contextFieldPhotoButton.hidden = !fieldPhotoUploadAvailable;
    const panelPhotoUploadButton = document.getElementById('panel-add-field-photo');
    if (panelPhotoUploadButton) {
        panelPhotoUploadButton.hidden = !fieldPhotoUploadAvailable;
        panelPhotoUploadButton.disabled = !fieldPhotoUploadAvailable;
    }
    if (!fieldPhotoUploadAvailable) cancelFieldPhotoLocationPick({ clearStatus: true });
    const reportPhotosSection = document.getElementById('report-photos-section');
    if (reportPhotosSection) reportPhotosSection.hidden = !photoUploadsAllowed;
    if (!photoUploadsAllowed) {
        const reportPhotos = document.getElementById('report-photos');
        if (reportPhotos) {
            reportPhotos.value = '';
            updateFilePickerSummary(reportPhotos);
        }
    }
}

function updatePublicFeatureAccess() {
    updateAdminPublicFeatureControls();
    updatePublicFeatureControlVisibility();
}

function applyPublicFeatureSettings(settings) {
    publicFeatureSettingsLoaded = true;
    publicFeatureSettings = normalizePublicFeatureSettings(settings);
    updatePublicFeatureAccess();
}

function applyPublicLayerSettings(settings) {
    publicLayerSettingsLoaded = true;
    publicLayerSettings = normalizePublicLayerSettings(settings);
    updatePublicLayerAccess();
    setCadastralLayerVisible(cadastralLayerVisible);
    setSurfaceLayerVisible(surfaceLayerVisible);
    updateMapSourceAvailability();
    if (savedWreckLayerVisible && publicLayerAllowed(PUBLIC_LAYER_KEYS.savedWrecks)) {
        placeSavedWrecks(savedWreckLayerData);
    } else {
        clearSavedWreckMarkers();
    }
    placeFieldPhotos(fieldPhotoLayerData);
    updateLingeringCarsCounter();
}

function setControlValue(id, value) {
    const el = enhancementControls[id];
    if (!el || value === undefined || value === null) return;
    if (el.type === 'checkbox') el.checked = Boolean(value);
    else el.value = String(value);
}

function enhancementFormSettings() {
    return {
        enabled: enhancementControls.enabled.checked,
        clahe_clip_limit: parseFloat(enhancementControls.clahe.value),
        clahe_tile_grid_size: parseInt(enhancementControls.tile.value),
        l_percentile_low: parseFloat(enhancementControls.pLow.value),
        l_percentile_high: parseFloat(enhancementControls.pHigh.value),
        l_output_low: parseFloat(enhancementControls.outLow.value),
        l_output_high: parseFloat(enhancementControls.outHigh.value),
        decast_strength: parseFloat(enhancementControls.decast.value),
    };
}

function applyEnhancementSettings(settings) {
    if (!settings) return;
    setControlValue('enabled', settings.enabled);
    setControlValue('clahe', settings.clahe_clip_limit);
    setControlValue('tile', settings.clahe_tile_grid_size);
    setControlValue('pLow', settings.l_percentile_low);
    setControlValue('pHigh', settings.l_percentile_high);
    setControlValue('outLow', settings.l_output_low);
    setControlValue('outHigh', settings.l_output_high);
    setControlValue('decast', settings.decast_strength);
    updateEnhancementLabels();
    updateEnhancementDefaultTicks();
}

function updateEnhancementLabels() {
    document.getElementById('enhancement-clahe-value').textContent = Number(enhancementControls.clahe.value).toFixed(1);
    document.getElementById('enhancement-tile-value').textContent = enhancementControls.tile.value;
    document.getElementById('enhancement-p-low-value').textContent = Number(enhancementControls.pLow.value).toFixed(1).replace('.0', '');
    document.getElementById('enhancement-p-high-value').textContent = Number(enhancementControls.pHigh.value).toFixed(1).replace('.0', '');
    document.getElementById('enhancement-out-low-value').textContent = enhancementControls.outLow.value;
    document.getElementById('enhancement-out-high-value').textContent = enhancementControls.outHigh.value;
    document.getElementById('enhancement-decast-value').textContent = Number(enhancementControls.decast.value).toFixed(2).replace(/0$/, '').replace(/\.$/, '');
}

function updateEnhancementDefaultTicks() {
    if (!defaultEnhancementSettings) return;
    Object.entries(enhancementControlFields).forEach(([controlId, field]) => {
        const control = enhancementControls[controlId];
        if (!control) return;
        const min = parseFloat(control.min);
        const max = parseFloat(control.max);
        const value = parseFloat(defaultEnhancementSettings[field]);
        const pct = max > min ? ((value - min) / (max - min)) * 100 : 0;
        control.style.setProperty('--default-pos', `${Math.max(0, Math.min(100, pct))}%`);
    });
}

function snapEnhancementControlToDefault(control) {
    if (!defaultEnhancementSettings || control.type !== 'range') return;
    const controlId = Object.keys(enhancementControls).find(key => enhancementControls[key] === control);
    const field = enhancementControlFields[controlId];
    if (!field) return;

    const current = parseFloat(control.value);
    const defaultValue = parseFloat(defaultEnhancementSettings[field]);
    const min = parseFloat(control.min);
    const max = parseFloat(control.max);
    const step = parseFloat(control.step || '1');
    const snapDistance = Math.max(step * 1.1, (max - min) * 0.015);
    if (Math.abs(current - defaultValue) <= snapDistance) {
        control.value = String(defaultValue);
    }
}

async function loadAppSettings() {
    let loadedPublicLayers = false;
    try {
        const data = await apiJson(SETTINGS_URL);
        defaultEnhancementSettings = data.defaults?.enhancement || data.enhancement;
        applyEnhancementSettings(data.enhancement);
        applyPublicLayerSettings(data.public_layers);
        applyPublicFeatureSettings(data.public_features);
        loadedPublicLayers = true;
    } catch (_) {
        updateEnhancementLabels();
    }
    if (!loadedPublicLayers) {
        publicLayerSettingsLoaded = true;
        publicFeatureSettingsLoaded = true;
        updatePublicLayerAccess();
        updatePublicFeatureAccess();
    }
}

async function saveSettings(payload, onSaved, options = {}) {
    const status = document.getElementById(options.statusId || 'settings-save-status');
    if (!adminAuthenticated) {
        updateSettingsAccess();
        return;
    }
    try {
        const data = await apiPostJson(SETTINGS_URL, payload);
        onSaved(data);
    } catch (err) {
        if (status) status.textContent = apiErrorMessage(err, options.errorMessage || t('modal.settings.saveError'));
    }
}

async function saveEnhancementSettings() {
    await saveSettings({ enhancement: enhancementFormSettings() }, data => {
        applyEnhancementSettings(data.enhancement);
        enhancementSettingsRevision = Date.now();
        refreshOrthoLayer();
        document.getElementById('settings-save-status').textContent = t('modal.settings.enhancementHint');
    });
}

async function savePublicLayerSettings() {
    await saveSettings({ public_layers: publicLayerFormSettings() }, data => {
        applyPublicLayerSettings(data.public_layers);
        const status = document.getElementById('admin-public-layers-status');
        if (status) status.textContent = t('modal.adminPanel.publicLayersSaved');
        loadSavedWrecks();
        loadFieldPhotos();
        updateMapSourceAvailability();
    }, {
        statusId: 'admin-public-layers-status',
        errorMessage: t('modal.adminPanel.publicLayersSaveError'),
    });
}

async function savePublicFeatureSettings() {
    await saveSettings({ public_features: publicFeatureFormSettings() }, data => {
        applyPublicFeatureSettings(data.public_features);
        const status = document.getElementById('admin-public-features-status');
        if (status) status.textContent = t('modal.adminPanel.publicFeaturesSaved');
        loadSavedWrecks();
        loadFieldPhotos();
    }, {
        statusId: 'admin-public-features-status',
        errorMessage: t('modal.adminPanel.publicFeaturesSaveError'),
    });
}

function photoRetentionReportSummary(report, state = {}) {
    if (!report) return t('modal.settings.photoRetentionIdle');
    const field = report.field_photos || {};
    const wreck = report.wreck_photos || {};
    const scanned = Number(field.scanned || 0) + Number(wreck.scanned || 0);
    const replaced = Number(field.replaced || 0) + Number(wreck.replaced || 0);
    const deleted = Number(field.deleted || 0) + Number(wreck.deleted || 0);
    const skipped = Number(field.skipped || 0) + Number(wreck.skipped || 0);
    const modeKey = report.dry_run
        ? 'modal.settings.photoRetentionSummaryDryRun'
        : 'modal.settings.photoRetentionSummaryApplied';
    return t(modeKey, {
        scanned,
        replaced,
        deleted,
        skipped,
        finished: state.last_finished_at || report.generated_at || '-',
    });
}

function updatePhotoRetentionStatus(state = {}) {
    const status = document.getElementById('photo-retention-status');
    if (!status) return;
    if (state.running) {
        status.textContent = t('modal.settings.photoRetentionRunning');
        return;
    }
    if (state.last_error) {
        status.textContent = t('modal.settings.photoRetentionLastError', { error: state.last_error });
        return;
    }
    status.textContent = photoRetentionReportSummary(state.last_report, state);
}

async function loadPhotoRetentionStatus() {
    if (!adminAuthenticated && !(await ensureAdmin())) return;
    const status = document.getElementById('photo-retention-status');
    if (status) status.textContent = t('modal.settings.photoRetentionLoading');
    try {
        const data = await apiJson(`${ADMIN_PHOTO_RETENTION_URL}?ts=${Date.now()}`, { cache: 'no-store' });
        if (data.status !== 'ok') {
            throw new Error(data.error || t('modal.settings.photoRetentionLoadError'));
        }
        updatePhotoRetentionStatus(data.retention || {});
    } catch (err) {
        if (status) status.textContent = apiErrorMessage(err, t('modal.settings.photoRetentionLoadError'));
    }
}

async function runPhotoRetention(dryRun = true) {
    if (!adminAuthenticated && !(await ensureAdmin())) return;
    if (!dryRun) {
        const confirmed = await confirmAction({
            title: t('modal.settings.photoRetentionApplyTitle'),
            message: t('modal.settings.photoRetentionApplyConfirm'),
            confirmLabel: t('modal.settings.photoRetentionApply'),
        });
        if (!confirmed) return;
    }
    const status = document.getElementById('photo-retention-status');
    if (status) status.textContent = t('modal.settings.photoRetentionRunning');
    try {
        const data = await apiPostJson(`${ADMIN_PHOTO_RETENTION_URL}/run`, { dry_run: Boolean(dryRun) });
        if (data.status !== 'ok') {
            throw new Error(data.error || t('modal.settings.photoRetentionRunError'));
        }
        updatePhotoRetentionStatus(data.retention || { last_report: data.report });
    } catch (err) {
        if (status) status.textContent = apiErrorMessage(err, t('modal.settings.photoRetentionRunError'));
    }
}

function queueEnhancementSettingsSave(event = null) {
    if (!adminAuthenticated) {
        updateSettingsAccess();
        return;
    }
    if (event?.target instanceof HTMLInputElement) {
        snapEnhancementControlToDefault(event.target);
    }
    updateEnhancementLabels();
    if (settingsSaveTimer) clearTimeout(settingsSaveTimer);
    settingsSaveTimer = setTimeout(saveEnhancementSettings, ENHANCEMENT_SETTINGS_SAVE_DEBOUNCE_MS);
}

Object.values(enhancementControls).forEach(control => {
    if (!control) return;
    const eventName = control.type === 'checkbox' ? 'change' : 'input';
    control.addEventListener(eventName, queueEnhancementSettingsSave);
});
document.getElementById('enhancement-reset')?.addEventListener('click', () => {
    if (!defaultEnhancementSettings) return;
    applyEnhancementSettings(defaultEnhancementSettings);
    queueEnhancementSettingsSave();
});

updateSettingsAccess();
loadAppSettings();
setCadastralLayerVisible(cadastralLayerVisible);
setSurfaceLayerVisible(surfaceLayerVisible);
