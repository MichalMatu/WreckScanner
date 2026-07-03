// Centralna konfiguracja frontendu. Zmiany tutaj wpływają tylko na zachowanie
// przeglądarki; limity bezpieczeństwa backendu są osobno egzekwowane w Pythonie.

// Klucze localStorage. Zmiana nazwy resetuje zapisane preferencje użytkownika.
const MODAL_POSITION_STORAGE_PREFIX = 'wroclaw-ortho-modal-position:';
const MAP_VIEW_STORAGE_KEY = 'wreckscanner.mapView.v2';
const WELCOME_MODAL_SEEN_STORAGE_KEY = 'wreckscanner.welcomeSeen.v1';
const CADASTRAL_LAYER_VISIBLE_STORAGE_KEY = 'wroclaw-ortho-cadastral-visible';

// Endpointy są relatywne, żeby aplikacja działała przez tunel/proxy bez
// twardego hosta i portu w JS.
const SETTINGS_URL = '/api/settings';
const WRECKS_URL = '/api/wrecks';
const FIELD_PHOTOS_URL = '/api/field-photos';
const CADASTRAL_IDENTIFY_URL = '/api/cadastral/identify';
const ADMIN_STATUS_URL = '/api/admin/status';
const ADMIN_LOGIN_URL = '/api/admin/login';
const ADMIN_LOGOUT_URL = '/api/admin/logout';
const ADMIN_PHOTOS_URL = '/api/admin/photos';
const ADMIN_WRECKS_URL = '/api/admin/wrecks';
const ADMIN_PRIVACY_REQUESTS_URL = '/api/admin/privacy-requests';
const ADMIN_PHOTO_RETENTION_URL = '/api/admin/photo-retention';

const PUBLIC_LAYER_KEYS = {
    vehicles: 'vehicles',
    fieldPhotoInfrastructure: 'field_photo_infrastructure',
    fieldPhotoSmoke: 'field_photo_smoke',
    fieldPhotoPending: 'field_photo_pending',
    cadastral: 'cadastral',
    baseMapOsm: 'base_map_osm',
};

const PUBLIC_FEATURE_KEYS = {
    manualWrecks: 'manual_wrecks',
    photoUploads: 'photo_uploads',
};

// Źródła podkładu mapy w UI; frontend steruje tutaj wyłącznie podglądem w Leaflet.
const OSM_TILE_URL = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';
const CARTO_LABELS_TILE_URL = 'https://{s}.basemaps.cartocdn.com/light_only_labels/{z}/{x}/{y}{r}.png';
const GEOPORTAL_STANDARD_WMTS_TILE_URL =
    'https://mapy.geoportal.gov.pl/wss/service/PZGIK/ORTO/WMTS/StandardResolution' +
    '?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0' +
    '&LAYER=ORTOFOTOMAPA&STYLE=default&FORMAT=image/jpeg' +
    '&TILEMATRIXSET=EPSG:3857&TILEMATRIX=EPSG:3857:{z}' +
    '&TILEROW={y}&TILECOL={x}';
const MAP_SOURCES = [
    { key: 'wroclaw-2020', shortLabel: '2020', label: 'Wrocław 2020', type: 'wroclaw', year: 2020 },
    { key: 'wroclaw-2021', shortLabel: '2021', label: 'Wrocław 2021', type: 'wroclaw', year: 2021 },
    { key: 'wroclaw-2022', shortLabel: '2022', label: 'Wrocław 2022', type: 'wroclaw', year: 2022 },
    { key: 'wroclaw-2023', shortLabel: '2023', label: 'Wrocław 2023', type: 'wroclaw', year: 2023 },
    { key: 'wroclaw-2024', shortLabel: '2024', label: 'Wrocław 2024', type: 'wroclaw', year: 2024 },
    { key: 'wroclaw-2025', shortLabel: '2025', label: 'Wrocław 2025', type: 'wroclaw', year: 2025 },
    {
        key: 'openstreetmap',
        shortLabel: 'OSM',
        label: 'OpenStreetMap',
        type: 'tile',
        url: OSM_TILE_URL,
        maxNativeZoom: 19,
        attribution: 'OpenStreetMap contributors',
        labelsOverlay: false,
        publicLayerKey: PUBLIC_LAYER_KEYS.baseMapOsm,
    },
    {
        key: 'poland-ortho',
        shortLabel: 'POL',
        label: 'Polska ortofoto',
        type: 'tile',
        url: GEOPORTAL_STANDARD_WMTS_TILE_URL,
        maxNativeZoom: 19,
        attribution: 'Geoportal.gov.pl / GUGiK',
    },
];
const DEFAULT_MAP_SOURCE_KEY = 'poland-ortho';
const CADASTRAL_WMS_URL = 'https://integracja.gugik.gov.pl/cgi-bin/KrajowaIntegracjaEwidencjiGruntow';
const CADASTRAL_WMS_LAYERS = 'dzialki,numery_dzialek';
const DEFAULT_MAP_VIEW = {
    center: [52.1, 19.4],
    zoom: 7,
};
const MAX_MAP_ZOOM = 22;
const METERS_PER_DEGREE_LAT = 111320;

// Przy dalekim oddaleniu pinezki przechodzą w małe klikane kropki.
// Do tego momentu zachowują liczniki zdjęć.
const MARKER_DETAIL_DOT_MAX_ZOOM = 16;
const MAP_POPUP_PREVIEW_MAX_IMAGES = 6;

// Uploady: backend dalej waliduje te same limity, frontend tylko daje szybszy
// komunikat przed wysłaniem formularza.
const WRECK_PHOTO_MAX_COUNT = 25;
const WRECK_PHOTO_MAX_BYTES = 10 * 1024 * 1024;
const FIELD_PHOTO_MAX_BYTES = 10 * 1024 * 1024;
const FIELD_PHOTO_MAX_FILES = 25;
const FIELD_PHOTO_EDIT_TOKEN_MIN_LENGTH = 8;
const FIELD_PHOTO_EDIT_TOKEN_MAX_LENGTH = 80;
const FIELD_PHOTO_ALLOWED_TYPES = new Set(['image/jpeg', 'image/png', 'image/webp']);
const FIELD_PHOTO_ISSUE_TYPE_VEHICLE = 'vehicle';
const FIELD_PHOTO_ISSUE_TYPES = new Set([
    FIELD_PHOTO_ISSUE_TYPE_VEHICLE,
    'infrastructure',
    'smoke',
]);
const FIELD_PHOTO_PUBLIC_LAYER_KEYS = {
    vehicle: PUBLIC_LAYER_KEYS.vehicles,
    infrastructure: PUBLIC_LAYER_KEYS.fieldPhotoInfrastructure,
    smoke: PUBLIC_LAYER_KEYS.fieldPhotoSmoke,
};

// Grupowanie zdjęć terenowych na mapie. 1 m jest celowo ciasne: większy promień
// scalał zdjęcia z sąsiednich pojazdów albo różnych stron tego samego parkingu.
const FIELD_PHOTO_GROUP_RADIUS_M = 1;
// Maksymalna odległość przeciągniętej pinezki zdjęć od sprawy pojazdu, przy której zdjęcia
// są przenoszone do tej sprawy i znikają z warstwy zdjęć terenowych.
const FIELD_PHOTO_ATTACH_TO_WRECK_RADIUS_M = 1;

// Timery UI. Krótsze wartości dają szybszą reakcję kosztem większej liczby
// requestów/przełączeń warstw; dłuższe uspokajają słabsze urządzenia.
const ORTHO_LAYER_SWAP_FALLBACK_MS = 3000;
const ENHANCEMENT_SETTINGS_SAVE_DEBOUNCE_MS = 350;
