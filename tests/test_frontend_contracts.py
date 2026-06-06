import re
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent


def read_web_styles() -> str:
    web_dir = ROOT_DIR / "web"
    entry = (web_dir / "styles.css").read_text(encoding="utf-8")
    chunks = [entry]
    for imported in re.findall(r'@import url\("/([^"]+)"\);', entry):
        chunks.append((web_dir / imported).read_text(encoding="utf-8"))
    return "\n".join(chunks)


def read_web_app_scripts() -> str:
    web_dir = ROOT_DIR / "web"
    html = (web_dir / "index.html").read_text(encoding="utf-8")
    script_paths = [
        path
        for path in re.findall(r'<script src="/([^"]+\.js)"></script>', html)
        if path == "app.js" or path.startswith("app/")
    ]
    return "\n".join((web_dir / path).read_text(encoding="utf-8") for path in script_paths)


def read_frontend_module_contract_sources() -> tuple[str, ...]:
    html = (ROOT_DIR / "web" / "index.html").read_text(encoding="utf-8")
    app_main_js = (ROOT_DIR / "web" / "app.js").read_text(encoding="utf-8")
    bootstrap_js = (ROOT_DIR / "web" / "app" / "bootstrap.js").read_text(encoding="utf-8")
    map_sources_js = (ROOT_DIR / "web" / "app" / "map_sources.js").read_text(encoding="utf-8")
    popups_js = (ROOT_DIR / "web" / "app" / "popups.js").read_text(encoding="utf-8")
    map_markers_js = (ROOT_DIR / "web" / "app" / "map_markers.js").read_text(encoding="utf-8")
    layers_js = (ROOT_DIR / "web" / "app" / "layers.js").read_text(encoding="utf-8")
    scan_area_js = (ROOT_DIR / "web" / "app" / "scan_area.js").read_text(encoding="utf-8")
    file_picker_js = (ROOT_DIR / "web" / "app" / "file_picker.js").read_text(encoding="utf-8")
    map_controls_js = (ROOT_DIR / "web" / "app" / "map_controls.js").read_text(encoding="utf-8")
    scan_progress_js = (ROOT_DIR / "web" / "app" / "scan_progress.js").read_text(encoding="utf-8")
    scan_js = (ROOT_DIR / "web" / "app" / "scan.js").read_text(encoding="utf-8")
    saved_wrecks_js = (ROOT_DIR / "web" / "app" / "saved_wrecks.js").read_text(encoding="utf-8")
    field_photos_js = (ROOT_DIR / "web" / "app" / "field_photos.js").read_text(encoding="utf-8")
    field_photo_actions_js = (ROOT_DIR / "web" / "app" / "field_photo_actions.js").read_text(encoding="utf-8")
    field_photo_popups_js = (ROOT_DIR / "web" / "app" / "field_photo_popups.js").read_text(encoding="utf-8")
    field_photo_upload_js = (ROOT_DIR / "web" / "app" / "field_photo_upload.js").read_text(encoding="utf-8")
    photo_review_js = (ROOT_DIR / "web" / "app" / "photo_review.js").read_text(encoding="utf-8")
    wreck_review_js = (ROOT_DIR / "web" / "app" / "wreck_review.js").read_text(encoding="utf-8")
    photo_review_canvas_js = (ROOT_DIR / "web" / "app" / "photo_review_canvas.js").read_text(encoding="utf-8")
    geotiff_cache_js = (ROOT_DIR / "web" / "app" / "geotiff_cache.js").read_text(encoding="utf-8")
    map_context_js = (ROOT_DIR / "web" / "app" / "map_context.js").read_text(encoding="utf-8")
    welcome_js = (ROOT_DIR / "web" / "app" / "welcome.js").read_text(encoding="utf-8")
    settings_js = (ROOT_DIR / "web" / "app" / "settings.js").read_text(encoding="utf-8")
    reports_js = (ROOT_DIR / "web" / "app" / "reports.js").read_text(encoding="utf-8")
    privacy_requests_js = (ROOT_DIR / "web" / "app" / "privacy_requests.js").read_text(encoding="utf-8")
    startup_js = (ROOT_DIR / "web" / "app" / "startup.js").read_text(encoding="utf-8")
    api_js = (ROOT_DIR / "web" / "app" / "api.js").read_text(encoding="utf-8")
    app_js = read_web_app_scripts()
    config_js = (ROOT_DIR / "web" / "config.js").read_text(encoding="utf-8")
    styles_entry = (ROOT_DIR / "web" / "styles.css").read_text(encoding="utf-8")
    styles = read_web_styles()
    return (
        html,
        app_main_js,
        bootstrap_js,
        map_sources_js,
        popups_js,
        map_markers_js,
        layers_js,
        scan_area_js,
        file_picker_js,
        map_controls_js,
        scan_progress_js,
        scan_js,
        saved_wrecks_js,
        field_photos_js,
        field_photo_actions_js,
        field_photo_popups_js,
        field_photo_upload_js,
        photo_review_js,
        wreck_review_js,
        photo_review_canvas_js,
        geotiff_cache_js,
        map_context_js,
        welcome_js,
        settings_js,
        reports_js,
        privacy_requests_js,
        startup_js,
        api_js,
        app_js,
        config_js,
        styles_entry,
        styles,
    )


def read_frontend_report_admin_contract_sources() -> dict[str, str]:
    return {
        "html": (ROOT_DIR / "web" / "index.html").read_text(encoding="utf-8"),
        "app_main_js": (ROOT_DIR / "web" / "app.js").read_text(encoding="utf-8"),
        "geotiff_cache_js": (ROOT_DIR / "web" / "app" / "geotiff_cache.js").read_text(encoding="utf-8"),
        "app_js": read_web_app_scripts(),
        "config_js": (ROOT_DIR / "web" / "config.js").read_text(encoding="utf-8"),
        "ui_js": (ROOT_DIR / "web" / "ui.js").read_text(encoding="utf-8"),
        "i18n_js": (ROOT_DIR / "web" / "i18n.js").read_text(encoding="utf-8"),
        "styles": read_web_styles(),
    }


def read_frontend_field_photo_contract_sources() -> dict[str, str]:
    return {
        "html": (ROOT_DIR / "web" / "index.html").read_text(encoding="utf-8"),
        "app_js": read_web_app_scripts(),
        "config_js": (ROOT_DIR / "web" / "config.js").read_text(encoding="utf-8"),
        "i18n_js": (ROOT_DIR / "web" / "i18n.js").read_text(encoding="utf-8"),
        "styles": read_web_styles(),
    }


def read_frontend_map_layer_contract_sources() -> dict[str, str]:
    return {
        "html": (ROOT_DIR / "web" / "index.html").read_text(encoding="utf-8"),
        "app_js": read_web_app_scripts(),
        "config_js": (ROOT_DIR / "web" / "config.js").read_text(encoding="utf-8"),
        "i18n_js": (ROOT_DIR / "web" / "i18n.js").read_text(encoding="utf-8"),
        "styles": read_web_styles(),
    }


class FrontendCacheSettingsContractTests(unittest.TestCase):
    def test_cache_select_exposes_no_limit_option(self):
        html = (ROOT_DIR / "web" / "index.html").read_text(encoding="utf-8")

        self.assertIn('id="geotiff-cache-limit"', html)
        self.assertIn('value="none"', html)
        self.assertIn('data-i18n="modal.settings.cacheNone"', html)

    def test_no_limit_option_round_trips_as_null_in_frontend_logic(self):
        app_js = read_web_app_scripts()

        self.assertIn("geotiffCacheControl?.value === 'none'", app_js)
        self.assertIn("return { max_gb: null }", app_js)
        self.assertIn("settings.max_gb === null", app_js)
        self.assertIn("geotiffCacheControl.value = 'none'", app_js)

    def test_no_limit_option_has_translations(self):
        i18n_js = (ROOT_DIR / "web" / "i18n.js").read_text(encoding="utf-8")

        self.assertIn("'modal.settings.cacheNone': 'Bez limitu'", i18n_js)
        self.assertIn("'modal.settings.cacheNone': 'No limit'", i18n_js)

    def test_frontend_modules_load_styles_and_scripts_in_order(self):
        (
            html,
            app_main_js,
            bootstrap_js,
            map_sources_js,
            popups_js,
            map_markers_js,
            layers_js,
            scan_area_js,
            file_picker_js,
            map_controls_js,
            scan_progress_js,
            scan_js,
            saved_wrecks_js,
            field_photos_js,
            field_photo_actions_js,
            field_photo_popups_js,
            field_photo_upload_js,
            photo_review_js,
            wreck_review_js,
            photo_review_canvas_js,
            geotiff_cache_js,
            map_context_js,
            welcome_js,
            settings_js,
            reports_js,
            privacy_requests_js,
            startup_js,
            api_js,
            app_js,
            config_js,
            styles_entry,
            styles,
        ) = read_frontend_module_contract_sources()

        self.assertNotIn("http://${window.location.hostname}:8000", app_js)
        for style_module in (
            "tokens.css",
            "base.css",
            "panel.css",
            "map.css",
            "popups.css",
            "modals.css",
            "forms.css",
            "review.css",
            "admin.css",
            "scan.css",
        ):
            self.assertIn(f'@import url("/styles/{style_module}");', styles_entry)
            self.assertTrue((ROOT_DIR / "web" / "styles" / style_module).exists())
        self.assertIn('<script src="/config.js"></script>', html)
        self.assertIn('<script src="/ui.js"></script>', html)
        self.assertIn('<script src="/admin.js"></script>', html)
        self.assertIn('<script src="/map_helpers.js"></script>', html)
        self.assertIn('<script src="/app/bootstrap.js"></script>', html)
        self.assertIn('<script src="/app/map_sources.js"></script>', html)
        self.assertIn('<script src="/app/popups.js"></script>', html)
        self.assertIn('<script src="/app/map_markers.js"></script>', html)
        self.assertIn('<script src="/app/layers.js"></script>', html)
        self.assertIn('<script src="/app/scan_area.js"></script>', html)
        self.assertIn('<script src="/app/file_picker.js"></script>', html)
        self.assertIn('<script src="/app/api.js"></script>', html)
        self.assertIn('<script src="/app/map_controls.js"></script>', html)
        self.assertIn('<script src="/app/scan_progress.js"></script>', html)
        self.assertIn('<script src="/app/scan.js"></script>', html)
        self.assertIn('<script src="/app/saved_wrecks.js"></script>', html)
        self.assertIn('<script src="/app/field_photos.js"></script>', html)
        self.assertIn('<script src="/app/field_photo_actions.js"></script>', html)
        self.assertIn('<script src="/app/field_photo_popups.js"></script>', html)
        self.assertIn('<script src="/app/field_photo_upload.js"></script>', html)
        self.assertIn('<script src="/app/photo_review.js"></script>', html)
        self.assertIn('<script src="/app/wreck_review.js"></script>', html)
        self.assertIn('<script src="/app/photo_review_canvas.js"></script>', html)
        self.assertIn('<script src="/app/geotiff_cache.js"></script>', html)
        self.assertIn('<script src="/app/map_context.js"></script>', html)
        self.assertIn('<script src="/app/welcome.js"></script>', html)
        self.assertIn('<script src="/app/settings.js"></script>', html)
        self.assertIn('<script src="/app/reports.js"></script>', html)
        self.assertIn('<script src="/app/privacy_requests.js"></script>', html)
        self.assertIn('<script src="/app/startup.js"></script>', html)
        self.assertLess(html.index('<script src="/config.js"></script>'), html.index('<script src="/app.js"></script>'))
        self.assertLess(html.index('<script src="/ui.js"></script>'), html.index('<script src="/app.js"></script>'))
        self.assertLess(html.index('<script src="/admin.js"></script>'), html.index('<script src="/app.js"></script>'))
        self.assertLess(
            html.index('<script src="/map_helpers.js"></script>'), html.index('<script src="/app.js"></script>')
        )
        self.assertLess(
            html.index('<script src="/map_helpers.js"></script>'),
            html.index('<script src="/app/bootstrap.js"></script>'),
        )
        self.assertLess(
            html.index('<script src="/app/bootstrap.js"></script>'),
            html.index('<script src="/app/map_sources.js"></script>'),
        )
        self.assertLess(
            html.index('<script src="/app/map_sources.js"></script>'), html.index('<script src="/app.js"></script>')
        )
        self.assertLess(
            html.index('<script src="/app/map_sources.js"></script>'),
            html.index('<script src="/app/popups.js"></script>'),
        )
        self.assertLess(
            html.index('<script src="/app/popups.js"></script>'),
            html.index('<script src="/app/map_markers.js"></script>'),
        )

    def test_frontend_module_map_sources_api_and_cache_contracts(self):
        (
            html,
            app_main_js,
            bootstrap_js,
            map_sources_js,
            popups_js,
            map_markers_js,
            layers_js,
            scan_area_js,
            file_picker_js,
            map_controls_js,
            scan_progress_js,
            scan_js,
            saved_wrecks_js,
            field_photos_js,
            field_photo_actions_js,
            field_photo_popups_js,
            field_photo_upload_js,
            photo_review_js,
            wreck_review_js,
            photo_review_canvas_js,
            geotiff_cache_js,
            map_context_js,
            welcome_js,
            settings_js,
            reports_js,
            privacy_requests_js,
            startup_js,
            api_js,
            app_js,
            config_js,
            styles_entry,
            styles,
        ) = read_frontend_module_contract_sources()

        self.assertLess(
            html.index('<script src="/app/map_markers.js"></script>'),
            html.index('<script src="/app/layers.js"></script>'),
        )
        self.assertLess(
            html.index('<script src="/app/popups.js"></script>'), html.index('<script src="/app.js"></script>')
        )
        self.assertLess(
            html.index('<script src="/app/layers.js"></script>'), html.index('<script src="/app.js"></script>')
        )
        self.assertLess(
            html.index('<script src="/app/layers.js"></script>'),
            html.index('<script src="/app/scan_area.js"></script>'),
        )
        self.assertLess(
            html.index('<script src="/app/scan_area.js"></script>'), html.index('<script src="/app.js"></script>')
        )
        self.assertLess(
            html.index('<script src="/app/scan_area.js"></script>'),
            html.index('<script src="/app/file_picker.js"></script>'),
        )
        self.assertLess(
            html.index('<script src="/app/file_picker.js"></script>'), html.index('<script src="/app.js"></script>')
        )
        self.assertLess(
            html.index('<script src="/app.js"></script>'), html.index('<script src="/app/map_controls.js"></script>')
        )
        self.assertLess(
            html.index('<script src="/app.js"></script>'), html.index('<script src="/app/api.js"></script>')
        )
        self.assertLess(
            html.index('<script src="/app/api.js"></script>'),
            html.index('<script src="/app/saved_wrecks.js"></script>'),
        )
        self.assertLess(
            html.index('<script src="/app.js"></script>'),
            html.index('<script src="/app/saved_wrecks.js"></script>'),
        )
        self.assertLess(
            html.index('<script src="/app/saved_wrecks.js"></script>'),
            html.index('<script src="/app/field_photos.js"></script>'),
        )
        self.assertLess(
            html.index('<script src="/app/field_photos.js"></script>'),
            html.index('<script src="/app/field_photo_actions.js"></script>'),
        )
        self.assertLess(
            html.index('<script src="/app/field_photo_actions.js"></script>'),
            html.index('<script src="/app/field_photo_popups.js"></script>'),
        )
        self.assertLess(
            html.index('<script src="/app/field_photo_popups.js"></script>'),
            html.index('<script src="/app/field_photo_upload.js"></script>'),
        )
        self.assertLess(
            html.index('<script src="/app/field_photo_upload.js"></script>'),
            html.index('<script src="/app/photo_review.js"></script>'),
        )
        self.assertLess(
            html.index('<script src="/app/photo_review.js"></script>'),
            html.index('<script src="/app/wreck_review.js"></script>'),
        )
        self.assertLess(
            html.index('<script src="/app/wreck_review.js"></script>'),
            html.index('<script src="/app/photo_review_canvas.js"></script>'),
        )
        self.assertLess(
            html.index('<script src="/app/photo_review_canvas.js"></script>'),
            html.index('<script src="/app/settings.js"></script>'),
        )

    def test_frontend_module_boundaries_for_map_scan_and_saved_wrecks(self):
        (
            html,
            app_main_js,
            bootstrap_js,
            map_sources_js,
            popups_js,
            map_markers_js,
            layers_js,
            scan_area_js,
            file_picker_js,
            map_controls_js,
            scan_progress_js,
            scan_js,
            saved_wrecks_js,
            field_photos_js,
            field_photo_actions_js,
            field_photo_popups_js,
            field_photo_upload_js,
            photo_review_js,
            wreck_review_js,
            photo_review_canvas_js,
            geotiff_cache_js,
            map_context_js,
            welcome_js,
            settings_js,
            reports_js,
            privacy_requests_js,
            startup_js,
            api_js,
            app_js,
            config_js,
            styles_entry,
            styles,
        ) = read_frontend_module_contract_sources()

        self.assertLess(
            html.index('<script src="/app/settings.js"></script>'),
            html.index('<script src="/app/reports.js"></script>'),
        )
        self.assertLess(
            html.index('<script src="/app/reports.js"></script>'),
            html.index('<script src="/app/privacy_requests.js"></script>'),
        )
        self.assertLess(
            html.index('<script src="/app/privacy_requests.js"></script>'),
            html.index('<script src="/app/map_controls.js"></script>'),
        )
        self.assertLess(
            html.index('<script src="/app/map_controls.js"></script>'),
            html.index('<script src="/app/scan_progress.js"></script>'),
        )
        self.assertLess(
            html.index('<script src="/app/scan_progress.js"></script>'),
            html.index('<script src="/app/scan.js"></script>'),
        )
        self.assertLess(
            html.index('<script src="/app/scan.js"></script>'),
            html.index('<script src="/app/geotiff_cache.js"></script>'),
        )
        self.assertLess(
            html.index('<script src="/app.js"></script>'), html.index('<script src="/app/map_context.js"></script>')
        )
        self.assertLess(
            html.index('<script src="/app.js"></script>'), html.index('<script src="/app/geotiff_cache.js"></script>')
        )
        self.assertLess(
            html.index('<script src="/app.js"></script>'), html.index('<script src="/app/scan_progress.js"></script>')
        )
        self.assertLess(
            html.index('<script src="/app/scan_progress.js"></script>'),
            html.index('<script src="/app/geotiff_cache.js"></script>'),
        )
        self.assertLess(
            html.index('<script src="/app/geotiff_cache.js"></script>'),
            html.index('<script src="/app/map_context.js"></script>'),
        )
        self.assertLess(
            html.index('<script src="/app/map_context.js"></script>'),
            html.index('<script src="/app/welcome.js"></script>'),
        )
        self.assertLess(
            html.index('<script src="/app/welcome.js"></script>'),
            html.index('<script src="/app/startup.js"></script>'),
        )
        self.assertIn("const API_URL = '/api/download'", config_js)
        self.assertIn("L.tileLayer.wms(`/wms_proxy/", app_js)
        self.assertIn("function buildMapSourceLayer(source)", app_js)
        self.assertIn("function setMapSource(index)", app_js)
        self.assertIn("function setMapSourceByVisiblePosition(position)", app_js)
        self.assertIn("function moveMapSource(delta)", app_js)
        self.assertIn("function renderMapSourceTicks(visibleIndices = visibleMapSourceIndices())", app_js)
        self.assertIn("function updateMapSourceAvailability()", app_js)
        self.assertIn("let currentMapSourceIndex", app_js)
        self.assertIn("visibleIndices.forEach(index =>", app_js)
        self.assertIn("tick.dataset.index = index", app_js)
        self.assertIn("tick.textContent = source.shortLabel", app_js)
        self.assertIn("tick.title = source.label", app_js)
        self.assertIn("range.max = Math.max(0, visibleIndices.length - 1)", app_js)
        self.assertIn("source.type === 'tile'", app_js)
        self.assertIn("function buildMapLabelLayer()", app_js)
        self.assertIn("activeMapSource().labelsOverlay !== false", app_js)
        self.assertIn("const OSM_TILE_URL = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'", config_js)
        self.assertIn(
            "const CARTO_LABELS_TILE_URL = 'https://{s}.basemaps.cartocdn.com/light_only_labels/{z}/{x}/{y}{r}.png'",
            config_js,
        )
        self.assertIn("shortLabel: 'OSM'", config_js)

    def test_frontend_module_field_photo_modules_stay_split(self):
        (
            html,
            app_main_js,
            bootstrap_js,
            map_sources_js,
            popups_js,
            map_markers_js,
            layers_js,
            scan_area_js,
            file_picker_js,
            map_controls_js,
            scan_progress_js,
            scan_js,
            saved_wrecks_js,
            field_photos_js,
            field_photo_actions_js,
            field_photo_popups_js,
            field_photo_upload_js,
            photo_review_js,
            wreck_review_js,
            photo_review_canvas_js,
            geotiff_cache_js,
            map_context_js,
            welcome_js,
            settings_js,
            reports_js,
            privacy_requests_js,
            startup_js,
            api_js,
            app_js,
            config_js,
            styles_entry,
            styles,
        ) = read_frontend_module_contract_sources()

        self.assertIn("publicLayerKey: PUBLIC_LAYER_KEYS.baseMapOsm", config_js)
        self.assertIn("const currentLabel = document.getElementById('year-current')", app_js)
        self.assertIn("currentLabel.textContent = source.shortLabel", app_js)
        self.assertIn("currentLabel.title = source.label", app_js)
        self.assertIn('grid-template-areas:\n            "prev track next"\n            ". current .";', styles)
        self.assertIn("width: min(420px, calc(100vw - 24px));", styles)
        self.assertIn("let mapSourceSwapToken = 0", app_js)
        self.assertIn("const swapToken = ++mapSourceSwapToken", app_js)
        self.assertIn("const map = L.map('map'", bootstrap_js)
        self.assertIn("function updateMarkerDetailMode()", bootstrap_js)
        self.assertNotIn("const map = L.map('map'", app_main_js)
        self.assertNotIn("function updateMarkerDetailMode()", app_main_js)
        self.assertIn("function buildMapSourceLayer(source)", map_sources_js)
        self.assertIn("mapSourceLayer = buildMapSourceLayer(activeMapSource()).addTo(map)", map_sources_js)
        self.assertNotIn("function buildMapSourceLayer(source)", app_main_js)
        self.assertNotIn("function setMapSource(index)", app_main_js)
        self.assertNotIn("let currentMapSourceIndex", app_main_js)
        self.assertNotIn("mapSourceLayer = buildMapSourceLayer(activeMapSource()).addTo(map)", app_main_js)
        self.assertIn("function popupPhotoGrid(previews", popups_js)
        self.assertIn("function photoPreviewGalleryItems(previews)", popups_js)
        self.assertIn("const galleryItems = photoPreviewGalleryItems(previews);", popups_js)
        self.assertIn("const photos = galleryItems.slice(0, maxItems);", popups_js)
        self.assertIn("JSON.stringify(galleryItems.map", popups_js)
        self.assertIn('data-photo-gallery="${galleryAttr}"', popups_js)
        self.assertIn('data-photo-gallery-index="${index}"', popups_js)
        self.assertIn("JSON.parse(grid.dataset.photoGallery)", popups_js)
        self.assertIn("function openPhotoPreviewModal(url", popups_js)
        self.assertNotIn("function popupPhotoGrid(previews", app_main_js)
        self.assertNotIn("function openPhotoPreviewModal(url", app_main_js)
        self.assertIn("class ApiError extends Error", api_js)
        self.assertIn("async function apiJson(url, options = {})", api_js)
        self.assertIn("async function apiPostJson(url, payload, options = {})", api_js)
        self.assertIn("async function apiPatchJson(url, payload, options = {})", api_js)
        self.assertIn("async function apiDeleteJson(url, options = {})", api_js)
        self.assertIn("function apiErrorMessage(error, fallback)", api_js)
        self.assertIn("const data = await apiJson(SETTINGS_URL)", settings_js)
        self.assertIn("const data = await apiPostJson(SETTINGS_URL, payload)", settings_js)
        self.assertIn("apiErrorMessage(err, options.errorMessage || t('modal.settings.saveError'))", settings_js)
        self.assertNotIn("fetch(SETTINGS_URL", settings_js)
        self.assertIn("const data = await apiJson(`${ADMIN_GEOTIFF_CACHE_URL}?ts=${Date.now()}`", geotiff_cache_js)
        self.assertIn("const data = await apiDeleteJson(`${ADMIN_GEOTIFF_CACHE_URL}/", geotiff_cache_js)
        self.assertIn("apiErrorMessage(err, t('modal.geotiffCache.loadError'))", geotiff_cache_js)
        self.assertNotIn("fetch(`${ADMIN_GEOTIFF_CACHE_URL}", geotiff_cache_js)
        self.assertIn("const data = await apiJson(`${ADMIN_PRIVACY_REQUESTS_URL}?status=", privacy_requests_js)
        self.assertIn("const data = await apiPatchJson(`${ADMIN_PRIVACY_REQUESTS_URL}/", privacy_requests_js)
        self.assertIn("apiErrorMessage(err, t('modal.privacyRequests.loadError'))", privacy_requests_js)
        self.assertNotIn("fetch(`${ADMIN_PRIVACY_REQUESTS_URL}", privacy_requests_js)
        self.assertIn("const data = await apiJson(`${ADMIN_WRECKS_URL}?${params.toString()}`", wreck_review_js)
        self.assertIn("const data = await apiPatchJson(`${ADMIN_WRECKS_URL}/", wreck_review_js)
        self.assertIn("const data = await apiDeleteJson(`${WRECKS_URL}/", wreck_review_js)
        self.assertIn("apiErrorMessage(err, t('modal.wreckReview.loadError'))", wreck_review_js)
        self.assertNotIn("fetch(`${ADMIN_WRECKS_URL}", wreck_review_js)
        self.assertNotIn("fetch(`${WRECKS_URL}/", wreck_review_js)
        self.assertIn("const data = await apiJson(`${WRECKS_URL}?ts=${Date.now()}`", saved_wrecks_js)
        self.assertIn("const data = await apiPostJson(WRECKS_URL, { rank })", saved_wrecks_js)
        self.assertIn(
            "const data = await apiPostJson(WRECKS_URL, { lat: latNumber, lon: lonNumber, cropM })", saved_wrecks_js
        )
        self.assertIn("const data = await apiPatchJson(`${ADMIN_WRECKS_URL}/", saved_wrecks_js)
        self.assertIn("const data = await apiDeleteJson(`${WRECKS_URL}/", saved_wrecks_js)
        self.assertIn("apiErrorMessage(err, t('wreck.reviewError'))", saved_wrecks_js)
        self.assertNotIn("fetch(WRECKS_URL", saved_wrecks_js)
        self.assertNotIn("fetch(`${WRECKS_URL}", saved_wrecks_js)
        self.assertNotIn("fetch(`${ADMIN_WRECKS_URL}", saved_wrecks_js)
        self.assertIn("const data = await apiJson(`${FIELD_PHOTOS_URL}?ts=${Date.now()}`", field_photos_js)
        self.assertNotIn("fetch(", field_photos_js)
        self.assertIn(
            "const data = await apiJson(FIELD_PHOTOS_URL, { method: 'POST', body: formData })", field_photo_upload_js
        )
        self.assertNotIn("fetch(", field_photo_upload_js)
        self.assertIn("const data = await apiPatchJson(`${ADMIN_PHOTOS_URL}/field/", field_photo_actions_js)
        self.assertIn("const data = await apiPatchJson(`${FIELD_PHOTOS_URL}/", field_photo_actions_js)
        self.assertIn("const data = await apiPostJson(`${WRECKS_URL}/", field_photo_actions_js)
        self.assertIn("const saveData = await apiPostJson(WRECKS_URL", field_photo_actions_js)
        self.assertIn("const data = await apiDeleteJson(`${FIELD_PHOTOS_URL}/", field_photo_actions_js)
        self.assertIn("apiErrorMessage(err, t('fieldPhoto.prepareCaseError'))", field_photo_actions_js)
        self.assertNotIn("fetch(", field_photo_actions_js)
        self.assertIn("const data = await apiPostJson(`${FIELD_PHOTOS_URL}/owner-claim`", photo_review_js)
        self.assertIn("const data = await apiJson(`${ADMIN_PHOTOS_URL}?${params.toString()}`", photo_review_js)

    def test_frontend_module_photo_and_wreck_review_modules_stay_split(self):
        (
            html,
            app_main_js,
            bootstrap_js,
            map_sources_js,
            popups_js,
            map_markers_js,
            layers_js,
            scan_area_js,
            file_picker_js,
            map_controls_js,
            scan_progress_js,
            scan_js,
            saved_wrecks_js,
            field_photos_js,
            field_photo_actions_js,
            field_photo_popups_js,
            field_photo_upload_js,
            photo_review_js,
            wreck_review_js,
            photo_review_canvas_js,
            geotiff_cache_js,
            map_context_js,
            welcome_js,
            settings_js,
            reports_js,
            privacy_requests_js,
            startup_js,
            api_js,
            app_js,
            config_js,
            styles_entry,
            styles,
        ) = read_frontend_module_contract_sources()

        self.assertIn("const data = await apiPatchJson(endpoint, payload)", photo_review_js)
        self.assertIn("const data = await apiDeleteJson(endpoint)", photo_review_js)
        self.assertIn("apiErrorMessage(err, t('modal.photoReview.saveError'))", photo_review_js)
        self.assertIn("const resp = await fetch(item.original_image", photo_review_js)
        self.assertEqual(photo_review_js.count("fetch("), 1)
        self.assertIn("const data = await apiJson(`${WRECKS_URL}/${encodeURIComponent(wreckId)}/photos`", reports_js)
        self.assertIn(
            "const data = await apiJson(`${WRECKS_URL}/${encodeURIComponent(wreckId)}/${reportPath}`", reports_js
        )
        self.assertIn("apiErrorMessage(err, t('modal.wreckPhoto.saveError'))", reports_js)
        self.assertIn("apiErrorMessage(err, t('wreck.reportPackageError'))", reports_js)
        self.assertIn("const resp = await fetch(url, { cache: 'no-store' })", reports_js)
        self.assertEqual(reports_js.count("fetch("), 1)
        self.assertIn("dlData = await apiPostJson(API_URL, { lat, lon, width, height })", scan_js)
        self.assertIn("const anData = await apiPostJson(ANALYZE_URL", scan_js)
        self.assertIn("const data = await apiPostJson('/api/inspect'", scan_js)
        self.assertNotIn("fetch(", scan_js)
        self.assertIn("const data = await apiJson(`${DOWNLOAD_PROGRESS_URL}?ts=${Date.now()}`", scan_progress_js)
        self.assertNotIn("fetch(", scan_progress_js)
        self.assertIn("const data = await apiJson(`${SURFACE_FEATURES_URL}?bbox=", layers_js)
        self.assertNotIn("fetch(", layers_js)
        self.assertIn("const data = await apiJson(url, { cache: 'no-store' })", map_context_js)
        self.assertNotIn("fetch(", map_context_js)
        self.assertIn("let pendingSubmissionLayer = L.layerGroup().addTo(map)", map_markers_js)
        self.assertIn("function addPendingSubmissionMarker({ lat, lon } = {})", map_markers_js)
        self.assertIn("function pendingFieldPhotoPopup(group)", map_markers_js)
        self.assertIn("function wreckIcon(photoCount = 0, reviewStatus = 'approved')", map_markers_js)
        self.assertNotIn("let pendingSubmissionLayer = L.layerGroup().addTo(map)", app_main_js)
        self.assertNotIn("function addPendingSubmissionMarker({ lat, lon } = {})", app_main_js)
        self.assertNotIn("function pendingFieldPhotoPopup(group)", app_main_js)
        self.assertNotIn("function wreckIcon(photoCount = 0, reviewStatus = 'approved')", app_main_js)
        self.assertIn("const surfacePane = map.createPane('surfacePane')", layers_js)
        self.assertIn("function buildCadastralLayer()", layers_js)
        self.assertIn("function setSurfaceLayerVisible(visible)", layers_js)
        self.assertNotIn("const surfacePane = map.createPane('surfacePane')", app_main_js)
        self.assertNotIn("function buildCadastralLayer()", app_main_js)
        self.assertNotIn("function setSurfaceLayerVisible(visible)", app_main_js)
        self.assertIn("function clampScanSize(value)", scan_area_js)
        self.assertIn("const snap = clampScanSize", scan_area_js)
        self.assertNotIn("function clampScanSize(value)", app_main_js)
        self.assertNotIn("const snap = clampScanSize", app_main_js)
        self.assertIn("function updateFilePickerSummary(input)", file_picker_js)
        self.assertIn("document.addEventListener('langchange', updateAllFilePickerSummaries)", file_picker_js)
        self.assertNotIn("function updateFilePickerSummary(input)", app_main_js)
        self.assertNotIn("document.addEventListener('langchange', updateAllFilePickerSummaries)", app_main_js)
        self.assertIn("L.control.zoom({ position: 'bottomright' }).addTo(map)", map_controls_js)
        self.assertIn("const range = document.getElementById('year-range')", map_controls_js)
        self.assertNotIn("L.control.zoom({ position: 'bottomright' }).addTo(map)", app_main_js)
        self.assertNotIn("const range = document.getElementById('year-range')", app_main_js)
        self.assertIn("function setStep(id, state, label = null, meta = null)", scan_progress_js)
        self.assertIn("function startDownloadProgressPolling()", scan_progress_js)
        self.assertIn("function resetProgress()", scan_progress_js)
        self.assertNotIn("function setStep(id, state, label = null, meta = null)", app_main_js)
        self.assertNotIn("function startDownloadProgressPolling()", app_main_js)
        self.assertNotIn("function resetProgress()", app_main_js)
        self.assertIn("async function runAll()", scan_js)
        self.assertIn("function placeMarkers(candidates, reportLink)", scan_js)
        self.assertIn("function selectedReviewCropM()", scan_js)
        self.assertNotIn("async function runAll()", app_main_js)
        self.assertNotIn("function placeMarkers(candidates, reportLink)", app_main_js)
        self.assertNotIn("function selectedReviewCropM()", app_main_js)
        self.assertIn("let savedWreckLayerData = []", saved_wrecks_js)
        self.assertIn("let savedWreckLayerVisible = true", saved_wrecks_js)
        self.assertIn("function safeWreckId(value)", saved_wrecks_js)
        self.assertIn("function savedWreckPopup(wreck)", saved_wrecks_js)
        self.assertIn("function placeSavedWrecks(wrecks = savedWreckLayerData)", saved_wrecks_js)
        self.assertIn("async function loadSavedWrecks()", saved_wrecks_js)
        self.assertIn("function toggleSavedWreckLayer(visible)", saved_wrecks_js)
        self.assertIn("async function saveWreck(rank, button = null)", saved_wrecks_js)
        self.assertIn("async function saveManualWreck(lat, lon, button = null)", saved_wrecks_js)
        self.assertIn("async function deleteWreck(wreckId, button = null)", saved_wrecks_js)

    def test_frontend_module_settings_reports_and_privacy_modules_stay_split(self):
        (
            html,
            app_main_js,
            bootstrap_js,
            map_sources_js,
            popups_js,
            map_markers_js,
            layers_js,
            scan_area_js,
            file_picker_js,
            map_controls_js,
            scan_progress_js,
            scan_js,
            saved_wrecks_js,
            field_photos_js,
            field_photo_actions_js,
            field_photo_popups_js,
            field_photo_upload_js,
            photo_review_js,
            wreck_review_js,
            photo_review_canvas_js,
            geotiff_cache_js,
            map_context_js,
            welcome_js,
            settings_js,
            reports_js,
            privacy_requests_js,
            startup_js,
            api_js,
            app_js,
            config_js,
            styles_entry,
            styles,
        ) = read_frontend_module_contract_sources()

        self.assertIn(
            "async function reviewWreckStatus(wreckId, publicReviewStatus, button = null)",
            saved_wrecks_js,
        )
        self.assertNotIn("let savedWreckLayerData = []", app_main_js)
        self.assertNotIn("let savedWreckLayerVisible = true", app_main_js)
        self.assertNotIn("function safeWreckId(value)", app_main_js)
        self.assertNotIn("function savedWreckPopup(wreck)", app_main_js)
        self.assertNotIn("function placeSavedWrecks(wrecks = savedWreckLayerData)", app_main_js)
        self.assertNotIn("async function loadSavedWrecks()", app_main_js)
        self.assertNotIn("function toggleSavedWreckLayer(visible)", app_main_js)
        self.assertNotIn("async function saveWreck(rank, button = null)", app_main_js)
        self.assertNotIn("async function saveManualWreck(lat, lon, button = null)", app_main_js)
        self.assertNotIn("async function deleteWreck(wreckId, button = null)", app_main_js)
        self.assertNotIn(
            "async function reviewWreckStatus(wreckId, publicReviewStatus, button = null)",
            app_main_js,
        )
        self.assertIn("let fieldPhotoLayerData = []", field_photos_js)
        self.assertIn("let fieldPhotoLocationPickActive = false", field_photo_upload_js)
        self.assertIn("function updateFieldPhotoIssueOptions()", field_photos_js)
        self.assertIn("function loadFieldPhotos()", field_photos_js)
        self.assertIn("function toggleFieldPhotoIssueFilter(issueType, visible)", field_photos_js)
        self.assertIn("function togglePendingFieldPhotoLayer(visible)", field_photos_js)
        self.assertIn("function countLingeringCars()", field_photos_js)
        self.assertIn("function updateLingeringCarsCounter()", field_photos_js)
        self.assertIn("async function rejectFieldPhotoGroup(encodedPhotoIds, button = null)", field_photo_actions_js)
        self.assertIn("async function updateFieldPhotoLocation(photo, lat, lon)", field_photo_actions_js)
        self.assertIn("function photoIdsForGroup(group)", field_photo_actions_js)
        self.assertIn("function nearestWreckForAttachment(lat, lon)", field_photo_actions_js)
        self.assertIn("async function attachFieldPhotoGroupToWreck(group, wreck)", field_photo_actions_js)
        self.assertIn("function decodeFieldPhotoIds(encodedPhotoIds)", field_photo_actions_js)
        self.assertIn("function fieldPhotosForReport(encodedPhotoIds)", field_photo_actions_js)
        self.assertIn("async function createManualWreckForFieldPhotoGroup(lat, lon)", field_photo_actions_js)
        self.assertIn("async function createWreckForFieldPhotoGroup(lat, lon, encodedPhotoIds)", field_photo_actions_js)
        self.assertIn(
            "async function openFieldPhotoGroupReport(lat, lon, encodedPhotoIds, button = null)", field_photo_actions_js
        )
        self.assertIn(
            "async function openFieldPhotoGroupPhotoUpload(lat, lon, encodedPhotoIds, issueType = FIELD_PHOTO_ISSUE_TYPE_VEHICLE, button = null)",
            field_photo_actions_js,
        )
        self.assertIn("async function updateFieldPhotoGroupLocation(group, marker)", field_photo_actions_js)
        self.assertIn("async function deleteFieldPhotoGroup(encodedPhotoIds, button = null)", field_photo_actions_js)
        self.assertIn("function fieldPhotoSourceLabel(source)", field_photo_popups_js)
        self.assertIn("function cacheBustedUrl(url, ts = Date.now())", field_photo_popups_js)
        self.assertIn("function fieldPhotoPreview(photo, index = 0, ts = Date.now())", field_photo_popups_js)
        self.assertIn("function fieldPhotoGroupLinks(group, photos)", field_photo_popups_js)
        self.assertIn("function fieldPhotoGroupMeta(group, photos)", field_photo_popups_js)
        self.assertIn("function encodedFieldPhotoIdsForGroup(group)", field_photo_popups_js)
        self.assertIn("function fieldPhotoGroupActions(group)", field_photo_popups_js)
        self.assertIn("function fieldPhotoPendingReviewPopup(group)", field_photo_popups_js)
        self.assertIn("function fieldPhotoGroupPopup(group)", field_photo_popups_js)
        self.assertIn("let fieldPhotoUploadItems = []", field_photo_upload_js)
        self.assertIn("let fieldPhotoUploadFallbackLatLng = null", field_photo_upload_js)
        self.assertIn("function generateFieldPhotoEditToken()", field_photo_upload_js)
        self.assertIn("function copyFieldPhotoEditToken()", field_photo_upload_js)
        self.assertIn("function validateFieldPhotoEditToken(token, options = {})", field_photo_upload_js)
        self.assertIn("function startFieldPhotoLocationPick()", field_photo_upload_js)
        self.assertIn("async function handlePanelFieldPhotoLocationPick(e)", field_photo_upload_js)
        self.assertIn("function isFieldPhotoLocationPickActive()", field_photo_upload_js)
        self.assertIn("async function openFieldPhotoUploadFromPanel()", field_photo_upload_js)
        self.assertIn("async function openFieldPhotoUploadAtContextPoint()", field_photo_upload_js)
        self.assertIn("async function uploadFieldPhotoItems(items)", field_photo_upload_js)
        self.assertIn("async function submitFieldPhotoUpload(event)", field_photo_upload_js)
        self.assertIn("async function retryFailedFieldPhotoUploads()", field_photo_upload_js)
        self.assertIn("function openFieldPhotoThanksModal({ saved = 0, editToken = '' } = {})", field_photo_upload_js)
        self.assertIn("async function copyFieldPhotoThanksToken()", field_photo_upload_js)
        self.assertNotIn("let fieldPhotoLayerData = []", app_main_js)
        self.assertNotIn("let fieldPhotoUploadItems = []", app_main_js)
        self.assertNotIn("let fieldPhotoUploadItems = []", field_photos_js)
        self.assertNotIn("let fieldPhotoUploadFallbackLatLng = null", field_photos_js)
        self.assertNotIn("let fieldPhotoLocationPickActive = false", field_photos_js)
        self.assertNotIn("function validateFieldPhotoEditToken(token, options = {})", field_photos_js)
        self.assertNotIn("function startFieldPhotoLocationPick()", field_photos_js)
        self.assertNotIn("async function openFieldPhotoUploadFromPanel()", field_photos_js)
        self.assertNotIn("async function openFieldPhotoUploadAtContextPoint()", field_photos_js)
        self.assertNotIn("async function uploadFieldPhotoItems(items)", field_photos_js)

    def test_frontend_module_retired_map_source_contracts_do_not_return(self):
        (
            html,
            app_main_js,
            bootstrap_js,
            map_sources_js,
            popups_js,
            map_markers_js,
            layers_js,
            scan_area_js,
            file_picker_js,
            map_controls_js,
            scan_progress_js,
            scan_js,
            saved_wrecks_js,
            field_photos_js,
            field_photo_actions_js,
            field_photo_popups_js,
            field_photo_upload_js,
            photo_review_js,
            wreck_review_js,
            photo_review_canvas_js,
            geotiff_cache_js,
            map_context_js,
            welcome_js,
            settings_js,
            reports_js,
            privacy_requests_js,
            startup_js,
            api_js,
            app_js,
            config_js,
            styles_entry,
            styles,
        ) = read_frontend_module_contract_sources()

        self.assertNotIn("async function retryFailedFieldPhotoUploads()", field_photos_js)
        self.assertNotIn("function openFieldPhotoThanksModal({ saved = 0, editToken = '' } = {})", field_photos_js)
        self.assertNotIn("function startFieldPhotoLocationPick()", field_photos_js)
        self.assertNotIn("async function handlePanelFieldPhotoLocationPick(e)", field_photos_js)
        self.assertNotIn("function fieldPhotoSourceLabel(source)", field_photos_js)
        self.assertNotIn("function cacheBustedUrl(url, ts = Date.now())", field_photos_js)
        self.assertNotIn("function fieldPhotoPreview(photo, index = 0, ts = Date.now())", field_photos_js)
        self.assertNotIn("function fieldPhotoGroupLinks(group, photos)", field_photos_js)
        self.assertNotIn("function fieldPhotoGroupMeta(group, photos)", field_photos_js)
        self.assertNotIn("function encodedFieldPhotoIdsForGroup(group)", field_photos_js)
        self.assertNotIn("function fieldPhotoGroupActions(group)", field_photos_js)
        self.assertNotIn("function fieldPhotoPendingReviewPopup(group)", field_photos_js)
        self.assertNotIn("function fieldPhotoGroupPopup(group)", field_photos_js)
        self.assertNotIn("async function rejectFieldPhotoGroup(encodedPhotoIds, button = null)", field_photos_js)
        self.assertNotIn("async function updateFieldPhotoLocation(photo, lat, lon)", field_photos_js)
        self.assertNotIn("function photoIdsForGroup(group)", field_photos_js)
        self.assertNotIn("function nearestWreckForAttachment(lat, lon)", field_photos_js)
        self.assertNotIn("async function attachFieldPhotoGroupToWreck(group, wreck)", field_photos_js)
        self.assertNotIn("function decodeFieldPhotoIds(encodedPhotoIds)", field_photos_js)
        self.assertNotIn("function fieldPhotosForReport(encodedPhotoIds)", field_photos_js)
        self.assertNotIn("async function createManualWreckForFieldPhotoGroup(lat, lon)", field_photos_js)
        self.assertNotIn("async function createWreckForFieldPhotoGroup(lat, lon, encodedPhotoIds)", field_photos_js)
        self.assertNotIn(
            "async function openFieldPhotoGroupReport(lat, lon, encodedPhotoIds, button = null)", field_photos_js
        )
        self.assertNotIn("async function updateFieldPhotoGroupLocation(group, marker)", field_photos_js)
        self.assertNotIn("async function deleteFieldPhotoGroup(encodedPhotoIds, button = null)", field_photos_js)
        self.assertNotIn("function updateFieldPhotoIssueOptions()", app_main_js)
        self.assertNotIn("function loadFieldPhotos()", app_main_js)
        self.assertNotIn("function toggleFieldPhotoIssueFilter(issueType, visible)", app_main_js)
        self.assertNotIn("function togglePendingFieldPhotoLayer(visible)", app_main_js)
        self.assertNotIn("function countLingeringCars()", app_main_js)
        self.assertNotIn("function updateLingeringCarsCounter()", app_main_js)
        self.assertNotIn("function deleteFieldPhotoGroup(encodedPhotoIds, button = null)", app_main_js)
        self.assertNotIn("function fieldPhotosForReport(encodedPhotoIds)", app_main_js)
        self.assertIn("refreshAdminStatus().finally", startup_js)
        self.assertIn("loadSavedWrecks();", startup_js)
        self.assertIn("loadFieldPhotos();", startup_js)
        self.assertNotIn("refreshAdminStatus().finally", app_main_js)
        self.assertIn("let photoReviewItems = []", photo_review_js)
        self.assertIn("function openPhotoReviewModal()", photo_review_js)
        self.assertIn("async function loadPhotoReviewQueue()", photo_review_js)
        self.assertIn("async function savePhotoReviewStatus(publicReviewStatus)", photo_review_js)
        self.assertIn("async function deletePhotoReviewItem()", photo_review_js)
        self.assertIn("async function openPhotoReviewForWreck(wreckId)", photo_review_js)
        self.assertIn("async function openPhotoReviewForFieldPhotoGroup(encodedPhotoIds)", photo_review_js)
        self.assertIn("function openFieldPhotoOwnerEditor(encodedPhotoIds)", photo_review_js)
        self.assertIn("async function submitFieldPhotoOwnerToken(event)", photo_review_js)
        self.assertIn("async function photoReviewOriginalImageSrc(item)", photo_review_js)
        self.assertNotIn("let photoReviewItems = []", app_main_js)
        self.assertNotIn("function openPhotoReviewModal()", app_main_js)
        self.assertNotIn("async function loadPhotoReviewQueue()", app_main_js)
        self.assertNotIn("async function savePhotoReviewStatus(publicReviewStatus)", app_main_js)
        self.assertNotIn("async function deletePhotoReviewItem()", app_main_js)
        self.assertNotIn("async function openPhotoReviewForWreck(wreckId)", app_main_js)
        self.assertNotIn("async function openPhotoReviewForFieldPhotoGroup(encodedPhotoIds)", app_main_js)
        self.assertNotIn("function openFieldPhotoOwnerEditor(encodedPhotoIds)", app_main_js)
        self.assertNotIn("async function submitFieldPhotoOwnerToken(event)", app_main_js)
        self.assertNotIn("async function photoReviewOriginalImageSrc(item)", app_main_js)
        self.assertIn("let wreckReviewItems = []", wreck_review_js)
        self.assertIn("function openWreckReviewModal()", wreck_review_js)
        self.assertIn("function loadWreckReviewQueue()", wreck_review_js)
        self.assertIn("function saveWreckReviewStatus(publicReviewStatus)", wreck_review_js)
        self.assertIn("function deleteWreckReviewItem()", wreck_review_js)
        self.assertIn("function focusWreckReviewOnMap()", wreck_review_js)
        self.assertNotIn("let wreckReviewItems = []", app_main_js)
        self.assertNotIn("function openWreckReviewModal()", app_main_js)
        self.assertNotIn("function loadWreckReviewQueue()", app_main_js)
        self.assertNotIn("function saveWreckReviewStatus(publicReviewStatus)", app_main_js)
        self.assertNotIn("function deleteWreckReviewItem()", app_main_js)
        self.assertNotIn("function focusWreckReviewOnMap()", app_main_js)
        self.assertIn("function drawPhotoReviewCanvas()", photo_review_canvas_js)
        self.assertIn("function rotatePhotoRedaction(degrees)", photo_review_canvas_js)
        self.assertIn("function photoReviewCanvasMetrics", photo_review_canvas_js)

    def test_frontend_module_contract_continues_part_08(self):
        (
            html,
            app_main_js,
            bootstrap_js,
            map_sources_js,
            popups_js,
            map_markers_js,
            layers_js,
            scan_area_js,
            file_picker_js,
            map_controls_js,
            scan_progress_js,
            scan_js,
            saved_wrecks_js,
            field_photos_js,
            field_photo_actions_js,
            field_photo_popups_js,
            field_photo_upload_js,
            photo_review_js,
            wreck_review_js,
            photo_review_canvas_js,
            geotiff_cache_js,
            map_context_js,
            welcome_js,
            settings_js,
            reports_js,
            privacy_requests_js,
            startup_js,
            api_js,
            app_js,
            config_js,
            styles_entry,
            styles,
        ) = read_frontend_module_contract_sources()

        self.assertIn("PHOTO_REVIEW_HANDLE_HIT_RADIUS_PX = 18", photo_review_canvas_js)
        self.assertIn("canvas.addEventListener('pointerdown'", photo_review_canvas_js)
        self.assertIn("function capturePhotoReviewPointer(canvas, pointerId)", photo_review_canvas_js)
        self.assertIn("function normalizePhotoReviewRedaction(redaction)", photo_review_canvas_js)
        self.assertNotIn("function drawPhotoReviewCanvas()", app_main_js)
        self.assertNotIn("function rotatePhotoRedaction(degrees)", app_main_js)
        self.assertNotIn("function photoReviewCanvasMetrics", app_main_js)
        self.assertNotIn("PHOTO_REVIEW_HANDLE_HIT_RADIUS_PX", app_main_js)
        self.assertIn("function openGeotiffCacheModal()", geotiff_cache_js)
        self.assertIn("function renderGeotiffCacheStatus(data = {})", geotiff_cache_js)
        self.assertIn("function renderGeotiffCacheLayer(data = {})", geotiff_cache_js)
        self.assertNotIn("function openGeotiffCacheModal()", app_main_js)
        self.assertNotIn("function renderGeotiffCacheStatus(data = {})", app_main_js)
        self.assertNotIn("function renderGeotiffCacheLayer(data = {})", app_main_js)
        self.assertIn("function toggleCrosshairFromContextMenu()", map_context_js)
        self.assertIn("function identifyCadastralParcelAtContextPoint()", map_context_js)
        self.assertIn("function copyContextPlaceLink()", map_context_js)
        self.assertNotIn("function toggleCrosshairFromContextMenu()", app_main_js)
        self.assertNotIn("function identifyCadastralParcelAtContextPoint()", app_main_js)
        self.assertNotIn("function copyContextPlaceLink()", app_main_js)
        self.assertIn("function openWelcomeModalIfNeeded()", welcome_js)
        self.assertIn("function openWelcomeModalFromAdminPanel()", welcome_js)
        self.assertNotIn("function openWelcomeModalIfNeeded()", app_main_js)
        self.assertNotIn("function openWelcomeModalFromAdminPanel()", app_main_js)
        self.assertIn("function updateSettingsAccess()", settings_js)
        self.assertIn("function publicLayerAllowed(layerKey)", settings_js)
        self.assertIn("function publicFeatureAllowed(featureKey)", settings_js)
        self.assertIn("async function loadPhotoRetentionStatus()", settings_js)
        self.assertNotIn("function updateSettingsAccess()", app_main_js)
        self.assertNotIn("function publicLayerAllowed(layerKey)", app_main_js)
        self.assertNotIn("function publicFeatureAllowed(featureKey)", app_main_js)
        self.assertNotIn("async function loadPhotoRetentionStatus()", app_main_js)
        self.assertIn("async function openReportPackageModal(wreckId, options = {})", reports_js)
        self.assertIn("function appendReportPackageExtraPhotos(formData)", reports_js)
        self.assertIn("function submitWreckPhotoUpload(event)", reports_js)
        self.assertIn("function validateWreckPhotoFiles(files)", reports_js)
        self.assertNotIn("async function openReportPackageModal(wreckId, options = {})", app_main_js)
        self.assertNotIn("function appendReportPackageExtraPhotos(formData)", app_main_js)
        self.assertNotIn("function submitWreckPhotoUpload(event)", app_main_js)
        self.assertNotIn("function validateWreckPhotoFiles(files)", app_main_js)
        self.assertIn("function openPrivacyRequestsModal()", privacy_requests_js)
        self.assertIn("async function loadPrivacyRequestQueue()", privacy_requests_js)
        self.assertIn("async function savePrivacyRequestUpdate()", privacy_requests_js)
        self.assertNotIn("function openPrivacyRequestsModal()", app_main_js)
        self.assertNotIn("async function loadPrivacyRequestQueue()", app_main_js)
        self.assertNotIn("async function savePrivacyRequestUpdate()", app_main_js)
        self.assertNotIn("function setYear(", app_js)
        self.assertNotIn("let currentYear", app_js)
        self.assertNotIn("ORTHO_YEARS", app_js)

        set_source_slice = app_js[
            app_js.index("function setMapSource(index)") : app_js.index("mapSourceLayer = buildMapSourceLayer")
        ]
        self.assertNotIn("setView", set_source_slice)
        self.assertNotIn("fitBounds", set_source_slice)
        self.assertNotIn("panTo", set_source_slice)

    def test_report_admin_modals_and_panel_markup_exist(self):
        sources = read_frontend_report_admin_contract_sources()
        html = sources["html"]
        app_js = sources["app_js"]
        config_js = sources["config_js"]
        ui_js = sources["ui_js"]
        styles = sources["styles"]

        self.assertIn('id="modal-report-package"', html)
        self.assertIn('id="report-package-pdf"', html)
        self.assertIn('data-i18n="modal.report.downloadPdf"', html)
        self.assertIn('id="report-package-extra-photos"', html)
        self.assertIn('id="modal-wreck-photo-upload"', html)
        self.assertIn('id="wreck-photo-files"', html)
        self.assertIn('class="file-picker-input" id="wreck-photo-files"', html)
        self.assertIn('data-i18n="modal.wreckPhoto.chooseFiles"', html)
        self.assertIn('data-file-summary-for="wreck-photo-files"', html)
        self.assertIn('class="file-picker-input" id="report-photos"', html)
        self.assertIn('data-i18n="modal.report.choosePhotos"', html)
        self.assertIn('data-file-summary-for="report-photos"', html)
        self.assertIn('name="photos[]"', html)
        self.assertIn('id="open-photo-review"', html)
        self.assertIn('id="modal-photo-review"', html)
        self.assertIn('id="open-wreck-review"', html)
        self.assertIn('id="modal-wreck-review"', html)
        self.assertIn('id="open-privacy-requests"', html)
        self.assertIn('id="modal-privacy-requests"', html)
        self.assertIn('id="open-geotiff-cache"', html)
        self.assertIn('id="modal-geotiff-cache"', html)
        self.assertIn('id="geotiff-cache-list"', html)
        self.assertIn('id="open-admin-panel"', html)
        self.assertIn('id="modal-admin-panel"', html)
        self.assertIn('class="modal-backdrop modal-backdrop--floating" id="modal-admin-panel"', html)
        self.assertIn('class="modal modal--admin-panel draggable-modal"', html)
        self.assertIn('class="modal-header modal-drag-handle"', html)
        self.assertIn("const MODAL_POSITION_STORAGE_PREFIX", config_js)
        self.assertIn("`${MODAL_POSITION_STORAGE_PREFIX}${backdrop.id}`", ui_js)
        self.assertIn("function hideModalBackdrop(backdrop)", ui_js)
        self.assertIn("new CustomEvent('modalclose'", ui_js)
        self.assertIn('id="photo-retention-section"', html)
        self.assertIn('class="modal-section admin-panel-section admin-panel-section--retention"', html)
        self.assertIn('class="setting-actions retention-actions"', html)
        self.assertIn('id="photo-retention-status"', html)
        self.assertIn('id="admin-layer-saved-wrecks"', html)
        self.assertIn('id="admin-layer-cadastral"', html)
        self.assertIn('id="admin-layer-surface"', html)
        self.assertIn('id="admin-layer-base-map-osm"', html)
        self.assertIn('id="admin-public-layers-save"', html)
        self.assertIn('id="admin-feature-scan-analysis"', html)
        self.assertIn('id="admin-feature-yolo-wrecks"', html)
        self.assertIn('id="admin-feature-manual-wrecks"', html)
        self.assertIn('id="admin-feature-photo-uploads"', html)
        self.assertIn('id="admin-public-features-save"', html)
        self.assertIn('id="open-welcome-modal"', html)
        self.assertIn('onclick="openWelcomeModalFromAdminPanel()"', html)
        self.assertIn('id="context-add-field-photos"', html)
        self.assertIn('data-i18n="modal.adminPanel.publicLayers"', html)
        self.assertIn('data-i18n="modal.adminPanel.publicFeatures"', html)
        geotiff_cache_styles = styles[styles.index(".modal--geotiff-cache {") :]
        self.assertIn("position: absolute;", geotiff_cache_styles)
        self.assertIn("top: 72px;", geotiff_cache_styles)
        self.assertIn("right: 16px;", geotiff_cache_styles)
        self.assertIn("width: min(680px, calc(100vw - 24px));", geotiff_cache_styles)
        self.assertIn("pointer-events: auto;\n}", styles[styles.index(".modal--geotiff-cache {") :])
        self.assertIn('id="privacy-request-filter"', html)
        self.assertIn('id="privacy-request-admin-note"', app_js)
        self.assertIn('href="/privacy"', html)
        self.assertIn('href="/report"', html)
        self.assertIn('id="modal-admin-login"', html)
        self.assertIn('id="panel-title" data-i18n="panel.title">WreckScanner', html)
        self.assertIn('id="lingering-cars-badge"', html)
        self.assertIn('class="panel-title-wrap"', html)
        self.assertNotIn('id="lingering-cars-counter"', html)
        self.assertNotIn('data-i18n="panel.lingeringCars"', html)
        self.assertNotIn('class="sep lingering-cars-sep"', html)
        self.assertNotIn("panel-scan-trigger", html)
        self.assertNotIn("panel-title-stack", html)
        self.assertNotIn('data-i18n-attr="title:panel.scanTitle"', html)

    def test_report_admin_popup_previews_and_case_actions_exist(self):
        sources = read_frontend_report_admin_contract_sources()
        html = sources["html"]
        app_js = sources["app_js"]
        config_js = sources["config_js"]
        i18n_js = sources["i18n_js"]

        self.assertIn("openReportPackageModal('${wreckId}')", app_js)
        self.assertIn("openWreckPhotoModal('${wreckId}')", app_js)
        self.assertIn("function popupPhotoGrid(previews", app_js)
        self.assertIn("function popupPhotoSection(title, previews", app_js)
        self.assertIn("function openPhotoPreviewModal(url", app_js)
        self.assertIn("function movePhotoPreview(delta)", app_js)
        self.assertIn("function photoPreviewDisplay(photo", app_js)
        self.assertIn("function photoPreviewGalleryItems(previews)", app_js)
        self.assertIn("const galleryItems = photoPreviewGalleryItems(previews);", app_js)
        self.assertIn("const photos = galleryItems.slice(0, maxItems);", app_js)
        self.assertIn("JSON.stringify(galleryItems.map", app_js)
        self.assertIn("JSON.parse(grid.dataset.photoGallery)", app_js)
        self.assertIn("data-photo-gallery-index", app_js)
        self.assertIn("function photoReviewQueueDisplay(item", app_js)
        self.assertIn("data-photo-preview-url", app_js)
        self.assertIn("data-photo-preview-detail", app_js)
        self.assertIn('id="modal-photo-preview"', html)
        self.assertIn('id="photo-preview-image"', html)
        self.assertIn('id="photo-preview-prev"', html)
        self.assertIn('id="photo-preview-next"', html)
        self.assertIn('id="photo-preview-counter"', html)
        self.assertIn("'modal.photoPreview.mapCropYear': 'Ortofoto {year}'", i18n_js)
        self.assertIn("'modal.photoPreview.mapCropYear': 'Orthophoto {year}'", i18n_js)
        self.assertIn("const MAP_POPUP_PREVIEW_MAX_IMAGES = 6", config_js)
        self.assertIn("MAP_POPUP_PREVIEW_MAX_IMAGES", app_js)
        self.assertIn("wreck.field_photo_previews", app_js)
        self.assertIn("wreck.evidence_previews", app_js)
        self.assertNotIn("max: 3", app_js)
        self.assertNotIn("wreck.preview_photos", app_js)
        self.assertNotIn("wreck-popup-preview-download", app_js)
        self.assertNotIn("function linkedFieldPhotoCountForWreck", app_js)
        self.assertNotIn("function wreckBadgePhotoCount", app_js)
        self.assertIn("icon: wreckIcon(wreck.photo_count, wreck.public_review_status)", app_js)
        self.assertIn("const photoButton = publicFeatureAllowed(PUBLIC_FEATURE_KEYS.photoUploads)", app_js)
        self.assertNotIn("const photoButton = adminAuthenticated", app_js)
        self.assertIn("const reviewPhotoCount = Number(wreck.review_photo_count || 0)", app_js)
        self.assertIn("const reviewPhotosButton = adminAuthenticated && reviewPhotoCount > 0", app_js)
        self.assertIn("openPhotoReviewForWreck('${wreckId}')", app_js)
        self.assertIn("function reviewWreckStatus(wreckId, publicReviewStatus, button = null)", app_js)
        self.assertIn("function openWreckReviewModal()", app_js)
        self.assertIn("function loadWreckReviewQueue()", app_js)
        self.assertIn("function saveWreckReviewStatus(publicReviewStatus)", app_js)
        self.assertIn("function deleteWreckReviewItem()", app_js)
        self.assertIn("function focusWreckReviewOnMap()", app_js)
        self.assertIn("popupCompactLink(folder, t('wreck.openCaseShort')", app_js)
        self.assertIn("popupCompactLink(links.street_view, 'SV'", app_js)
        self.assertIn("popupCompactLink(links.google_maps_satellite, 'Sat'", app_js)
        self.assertIn('class="map-popup-actions"', app_js)
        self.assertIn("t('wreck.popup.fieldPhotos')", app_js)
        self.assertIn("t('wreck.popup.evidencePreviews')", app_js)
        self.assertIn("report-package", app_js)
        self.assertIn("async function openReportPackageModal(wreckId, options = {}) {", app_js)
        self.assertNotIn(
            "async function openReportPackageModal(wreckId, options = {}) {\n    if (!(await ensureAdmin())) return;",
            app_js,
        )
        self.assertIn("const reportPath = adminAuthenticated ? 'report-package' : 'public-report-package';", app_js)
        self.assertIn("document.getElementById('report-package-pdf').href = data.pdf_url || '#'", app_js)

    def test_report_admin_review_controls_and_canvas_contracts_exist(self):
        sources = read_frontend_report_admin_contract_sources()
        html = sources["html"]
        app_js = sources["app_js"]
        config_js = sources["config_js"]
        i18n_js = sources["i18n_js"]
        styles = sources["styles"]

        self.assertIn("rotatePhotoRedaction(5)", html)
        self.assertIn('class="review-tool-actions"', html)
        self.assertIn('class="review-decision-actions"', html)
        self.assertIn('class="report-copy-btn review-icon-btn"', html)
        self.assertIn('data-i18n-attr="title:modal.photoReview.undo;aria-label:modal.photoReview.undo"', html)
        self.assertIn('data-i18n-attr="title:modal.wreckReview.showOnMap;aria-label:modal.wreckReview.showOnMap"', html)
        self.assertIn('data-i18n="modal.photoReview.savePendingShort"', html)
        self.assertIn('data-i18n="modal.photoReview.deleteShort"', html)
        self.assertIn('data-i18n="modal.wreckReview.savePendingShort"', html)
        self.assertIn('data-i18n="modal.wreckReview.deleteShort"', html)
        self.assertIn('class="review-action-icon"', html)
        self.assertIn('class="review-action-label"', html)
        self.assertIn('data-i18n-attr="title:modal.photoReview.approve;aria-label:modal.photoReview.approve"', html)
        self.assertIn('data-i18n-attr="title:modal.wreckReview.approve;aria-label:modal.wreckReview.approve"', html)
        self.assertIn('id="photo-review-delete"', html)
        self.assertIn('onclick="deletePhotoReviewItem()"', html)
        self.assertIn("function rotatePhotoRedaction(degrees)", app_js)
        self.assertIn("function moveRedaction(redaction, dx, dy)", app_js)
        self.assertIn(
            "function redactionHandleAtPoint(point, redactionIndex = activePhotoReviewRedactionIndex)", app_js
        )
        self.assertIn("function resizeRedactionPoint(redaction, pointIndex, point)", app_js)
        self.assertIn("function photoReviewCanvasMetrics", app_js)
        self.assertIn("PHOTO_REVIEW_HANDLE_HIT_RADIUS_PX = 18", app_js)
        self.assertIn("const updateHoverState = event =>", app_js)
        self.assertIn("canvas.addEventListener('pointerdown'", app_js)
        self.assertIn("canvas.addEventListener('pointermove'", app_js)
        self.assertIn("function capturePhotoReviewPointer(canvas, pointerId)", app_js)
        self.assertIn("canvas.setPointerCapture?.(pointerId)", app_js)
        self.assertIn("function releasePhotoReviewPointer(canvas, pointerId)", app_js)
        self.assertNotIn("canvas.addEventListener('mousedown'", app_js)
        self.assertIn("canvas.classList.add('is-moving-redaction')", app_js)
        self.assertIn("canvas.classList.add('is-resizing-redaction')", app_js)
        self.assertIn("canvas.classList.add('is-hovering-handle')", app_js)
        self.assertIn("canvas.classList.add('is-hovering-redaction')", app_js)
        self.assertIn("#photo-review-canvas.is-moving-redaction", styles)
        self.assertIn("#photo-review-canvas.is-resizing-redaction", styles)
        self.assertIn("#photo-review-canvas.is-hovering-handle", styles)
        self.assertIn("#photo-review-canvas.is-hovering-redaction", styles)
        self.assertIn("touch-action: none", styles)
        self.assertIn(".review-icon-btn", styles)
        self.assertIn(".review-action-icon", styles)
        self.assertIn(".review-action-label", styles)
        self.assertIn(".review-decision-actions", styles)
        self.assertIn(".review-approve-btn", styles)
        self.assertIn("@media (max-width: 520px)", styles)
        self.assertIn("flex: 0 0 40px", styles)
        self.assertIn("normalizePhotoReviewRedaction", app_js)
        self.assertIn("function submitWreckPhotoUpload(event)", app_js)
        self.assertIn("function validateWreckPhotoFiles(files)", app_js)
        self.assertIn("function openPhotoReviewModal()", app_js)
        self.assertIn("function savePhotoReviewStatus(publicReviewStatus)", app_js)
        self.assertIn("function photoReviewDeleteEndpoint(item)", app_js)
        self.assertIn("function deletePhotoReviewItem()", app_js)
        self.assertIn("activePhotoReview?.public_review_status === 'rejected'", app_js)
        self.assertIn("method: 'DELETE'", app_js)
        self.assertIn("public_review_status: publicReviewStatus", app_js)
        self.assertIn("WRECK_PHOTO_MAX_COUNT = 25", config_js)
        self.assertIn("WRECK_PHOTO_MAX_BYTES = 10 * 1024 * 1024", config_js)
        self.assertIn("const ADMIN_PHOTOS_URL = '/api/admin/photos'", config_js)
        self.assertIn("const ADMIN_PRIVACY_REQUESTS_URL = '/api/admin/privacy-requests'", config_js)
        self.assertIn("const ADMIN_PHOTO_RETENTION_URL = '/api/admin/photo-retention'", config_js)
        self.assertIn("const ADMIN_WRECKS_URL = '/api/admin/wrecks'", config_js)
        self.assertIn("'modal.photoReview.delete': 'Usuń zdjęcie'", i18n_js)
        self.assertIn("'modal.photoReview.delete': 'Delete photo'", i18n_js)
        self.assertIn("'modal.photoReview.savePendingShort': 'Do weryfikacji'", i18n_js)
        self.assertIn("'modal.photoReview.savePendingShort': 'Needs review'", i18n_js)
        self.assertIn("'modal.photoReview.deleteShort': 'Usuń'", i18n_js)
        self.assertIn("'modal.photoReview.deleteShort': 'Delete'", i18n_js)
        self.assertIn("'modal.photoReview.approve': 'Zatwierdź'", i18n_js)
        self.assertIn("'modal.photoReview.approve': 'Approve'", i18n_js)
        self.assertIn("'modal.wreckReview.title': 'Przegląd spraw pojazdów'", i18n_js)
        self.assertIn("'modal.wreckReview.title': 'Vehicle case review'", i18n_js)
        self.assertIn("'modal.wreckReview.savePendingShort': 'Do weryfikacji'", i18n_js)
        self.assertIn("'modal.wreckReview.savePendingShort': 'Needs review'", i18n_js)
        self.assertIn("'modal.wreckReview.deleteShort': 'Usuń'", i18n_js)
        self.assertIn("'modal.wreckReview.deleteShort': 'Delete'", i18n_js)
        self.assertIn("'modal.wreckReview.approve': 'Zatwierdź'", i18n_js)
        self.assertIn("'modal.wreckReview.approve': 'Approve'", i18n_js)

    def test_report_admin_geotiff_privacy_retention_and_report_contracts_exist(self):
        sources = read_frontend_report_admin_contract_sources()
        app_main_js = sources["app_main_js"]
        geotiff_cache_js = sources["geotiff_cache_js"]
        app_js = sources["app_js"]
        config_js = sources["config_js"]
        i18n_js = sources["i18n_js"]
        styles = sources["styles"]

        self.assertIn("const ADMIN_GEOTIFF_CACHE_URL = '/api/admin/geotiff-cache'", config_js)
        self.assertIn("function openGeotiffCacheModal()", app_js)
        self.assertIn("function openGeotiffCacheModal()", geotiff_cache_js)
        self.assertNotIn("function openGeotiffCacheModal()", app_main_js)
        self.assertIn("function renderGeotiffCacheStatus(data = {})", app_js)
        self.assertIn("function renderGeotiffCacheStatus(data = {})", geotiff_cache_js)
        self.assertNotIn("function renderGeotiffCacheStatus(data = {})", app_main_js)
        self.assertIn("function clearGeotiffCacheLayer(options = {})", app_js)
        self.assertIn("function renderGeotiffCacheLayer(data = {})", app_js)
        self.assertIn("function renderGeotiffCacheLayer(data = {})", geotiff_cache_js)
        self.assertNotIn("function renderGeotiffCacheLayer(data = {})", app_main_js)
        self.assertIn("function selectGeotiffCacheItem(fileName, options = {})", app_js)
        self.assertIn("async function deleteGeotiffCacheItem(fileName, button = null)", app_js)
        self.assertIn("geotiffCacheRectanglesByFile.set(file, rect)", app_js)
        self.assertIn("geotiffCacheRectangleStyle(file === selectedGeotiffCacheFile)", app_js)
        self.assertIn("deleteGeotiffCacheItem(deleteButton.dataset.file, deleteButton)", app_js)
        self.assertIn('class="geotiff-cache-delete"', app_js)
        self.assertIn("`${ADMIN_GEOTIFF_CACHE_URL}/${encodeURIComponent(file)}`", app_js)
        self.assertIn("geotiffCacheLayer = L.layerGroup(rectangles).addTo(map)", app_js)
        self.assertIn(
            "document.getElementById('modal-geotiff-cache')?.addEventListener('modalclose', clearGeotiffCacheLayer)",
            app_js,
        )
        self.assertIn("function openPrivacyRequestsModal()", app_js)
        self.assertIn("async function loadPrivacyRequestQueue()", app_js)
        self.assertIn("async function savePrivacyRequestUpdate()", app_js)
        self.assertIn("async function loadPhotoRetentionStatus()", app_js)
        self.assertIn("async function runPhotoRetention(dryRun = true)", app_js)
        self.assertIn("'modal.settings.photoRetention': 'Retencja oryginałów'", i18n_js)
        self.assertIn("method: 'PATCH'", app_js)
        self.assertIn("'modal.privacyRequests.title': 'Zgłoszenia prywatności'", i18n_js)
        self.assertIn("'icon.privacyRequests': 'Zgłoszenia prywatności'", i18n_js)
        self.assertIn(".privacy-request-layout", styles)
        self.assertIn("`${WRECKS_URL}/${encodeURIComponent(wreckId)}/photos`", app_js)
        self.assertIn("REPORT_PHOTO_MAX_COUNT = 5", config_js)
        self.assertIn("REPORT_PHOTO_MAX_BYTES = 10 * 1024 * 1024", config_js)
        self.assertIn("const saveButton = yoloWrecksAllowed", app_js)
        self.assertNotIn("const saveButton = adminAuthenticated", app_js)
        self.assertNotIn("window.prompt", app_js)
        self.assertIn("'wreck.reportPackage': 'Generuj zgłoszenie do weryfikacji'", i18n_js)
        self.assertIn("'panel.lingeringCarsTooltip': 'Pojazdy udokumentowane zdjęciami w terenie'", i18n_js)
        self.assertNotIn("'panel.lingeringCars'", i18n_js)
        self.assertNotIn("'panel.scanTitle'", i18n_js)
        self.assertIn("'wreck.addPhotos': 'Dodaj zdjęcia'", i18n_js)
        self.assertIn("'modal.wreckPhoto.title': 'Zdjęcia do sprawy pojazdu'", i18n_js)
        self.assertIn("'modal.wreckPhoto.chooseFiles': 'Wybierz zdjęcia do sprawy'", i18n_js)
        self.assertIn("'modal.wreckPhoto.submit': 'Dodaj do sprawy'", i18n_js)
        self.assertIn("'modal.report.choosePhotos': 'Wybierz załączniki do zgłoszenia'", i18n_js)
        self.assertIn("'filePicker.empty': 'Nie wybrano plików'", i18n_js)
        self.assertIn("'filePicker.selectedMany': '{n} files selected'", i18n_js)
        self.assertIn("'modal.photoReview.title': 'Przegląd zdjęć'", i18n_js)
        self.assertIn("'modal.photoReview.search': 'Szukaj id / sprawy'", i18n_js)
        self.assertIn("'wreck.popup.title': 'Sprawa pojazdu'", i18n_js)
        self.assertIn("'wreck.popup.title': 'Vehicle case'", i18n_js)
        self.assertIn("'modal.geotiffCache.title': 'Cache GeoTIFF'", i18n_js)
        self.assertIn("'modal.geotiffCache.delete': 'Usuń kafel'", i18n_js)
        self.assertIn("'modal.geotiffCache.delete': 'Delete tile'", i18n_js)
        self.assertIn("'icon.geotiffCache': 'Cache GeoTIFF'", i18n_js)
        self.assertIn("'icon.welcomeModal': 'Pokaż powitanie'", i18n_js)
        self.assertIn(".geotiff-cache-item.is-selected", styles)
        self.assertIn(".geotiff-cache-delete", styles)
        self.assertIn("'wreck.reviewPhotos': 'Edytuj anonimizację'", i18n_js)
        self.assertIn("'wreck.approve': 'Zatwierdź sprawę'", i18n_js)
        self.assertIn("'footer.privacy': 'Prywatność'", i18n_js)
        self.assertIn("'footer.report': 'Zgłoś problem'", i18n_js)
        self.assertIn("'modal.wreckPhoto.fileCountError': 'Choose up to {n} photos at a time.'", i18n_js)
        self.assertIn("'modal.report.submit': 'Generate report'", i18n_js)
        self.assertIn("'modal.report.downloadPdf': 'Download PDF'", i18n_js)
        self.assertIn("'modal.report.title': 'Zgłoszenie do weryfikacji'", i18n_js)
        self.assertIn("'modal.report.title': 'Verification report'", i18n_js)

    def test_report_admin_panel_header_and_retired_scan_collapse_contracts_exist(self):
        sources = read_frontend_report_admin_contract_sources()
        html = sources["html"]
        app_js = sources["app_js"]
        ui_js = sources["ui_js"]
        i18n_js = sources["i18n_js"]
        styles = sources["styles"]

        self.assertIn("title.textContent = t('panel.title')", ui_js)
        self.assertIn('id="panel-header-toggle"', html)
        self.assertIn('onclick="togglePanel()"', html)
        self.assertIn('onkeydown="handlePanelHeaderToggleKey(event)"', html)
        self.assertIn("function handlePanelHeaderToggleKey(event)", ui_js)
        self.assertIn(".panel-header-toggle", styles)
        self.assertNotIn('id="toggle-panel"', html)
        self.assertNotIn("panel.scanCollapsed", app_js)
        self.assertNotIn("panel.scanCollapsed", ui_js)
        self.assertIn("'panel.title': 'WreckScanner'", i18n_js)
        self.assertNotIn("'panel.scanCollapsed'", i18n_js)

    def test_public_first_screen_has_single_photo_upload_cta(self):
        html = (ROOT_DIR / "web" / "index.html").read_text(encoding="utf-8")
        field_photo_upload_js = (ROOT_DIR / "web" / "app" / "field_photo_upload.js").read_text(encoding="utf-8")
        settings_js = (ROOT_DIR / "web" / "app" / "settings.js").read_text(encoding="utf-8")
        i18n_js = (ROOT_DIR / "web" / "i18n.js").read_text(encoding="utf-8")
        styles_entry = (ROOT_DIR / "web" / "styles.css").read_text(encoding="utf-8")
        styles = read_web_styles()

        self.assertIn('id="panel-add-field-photo"', html)
        self.assertIn('onclick="openFieldPhotoUploadFromPanel()" hidden', html)
        self.assertIn('aria-pressed="false"', html)
        self.assertIn('data-i18n="panel.addPhoto"', html)
        self.assertIn("data-panel-add-photo-label", html)
        self.assertIn("async function openFieldPhotoUploadFromPanel()", field_photo_upload_js)
        self.assertIn("function startFieldPhotoLocationPick()", field_photo_upload_js)
        self.assertIn("fieldPhotoLocationPickActive = true", field_photo_upload_js)
        self.assertIn("map.on('click', handlePanelFieldPhotoLocationPick)", field_photo_upload_js)
        self.assertIn("map.off('click', handlePanelFieldPhotoLocationPick)", field_photo_upload_js)
        self.assertIn("async function handlePanelFieldPhotoLocationPick(e)", field_photo_upload_js)
        self.assertIn("fallbackLatLng,", field_photo_upload_js)
        self.assertIn("ignoreExifGps: true", field_photo_upload_js)
        self.assertIn(
            "isFieldPhotoLocationPickActive()", (ROOT_DIR / "web" / "app" / "scan.js").read_text(encoding="utf-8")
        )
        self.assertIn("const panelPhotoUploadButton = document.getElementById('panel-add-field-photo')", settings_js)
        self.assertIn("panelPhotoUploadButton.hidden = !fieldPhotoUploadAvailable", settings_js)
        self.assertIn(
            "if (!fieldPhotoUploadAvailable) cancelFieldPhotoLocationPick({ clearStatus: true });", settings_js
        )
        self.assertIn("'panel.addPhoto': 'Dodaj zdjęcie'", i18n_js)
        self.assertIn("'panel.addPhotoPicking': 'Wskaż miejsce'", i18n_js)
        self.assertIn("'panel.addPhotoTitle': 'Wskaż miejsce zdjęcia na mapie'", i18n_js)
        self.assertIn("'panel.addPhotoPickStatus': 'Kliknij miejsce na mapie, w którym chcesz dodać zdjęcie.'", i18n_js)
        self.assertIn("'panel.addPhoto': 'Add photo'", i18n_js)
        self.assertIn("'panel.addPhotoPicking': 'Pick location'", i18n_js)
        self.assertIn(".panel-primary-actions", styles)
        self.assertIn(".panel-photo-cta", styles)
        self.assertIn(".panel-photo-cta.is-picking-location", styles)
        self.assertIn(".leaflet-container.is-picking-field-photo-location", styles)
        self.assertNotIn('class="footer"', html)
        self.assertNotIn('class="social-links"', html)
        self.assertNotIn('href="https://www.facebook.com/WreckScanner/"', html)
        self.assertNotIn('@import url("/styles/footer.css");', styles_entry)
        self.assertIn("'modal.admin.title': 'Panel administratora'", i18n_js)
        self.assertIn(".panel-title-wrap", styles)
        self.assertIn(".lingering-cars-badge", styles)
        self.assertNotIn(".lingering-cars-counter", styles)
        self.assertNotIn("hr.lingering-cars-sep", styles)
        self.assertNotIn(".panel-scan-trigger", styles)
        self.assertNotIn(".panel-title-stack", styles)

    def test_language_control_lives_inside_compact_settings_modal_without_duplicate_help(self):
        html = (ROOT_DIR / "web" / "index.html").read_text(encoding="utf-8")
        app_js = read_web_app_scripts()
        ui_js = (ROOT_DIR / "web" / "ui.js").read_text(encoding="utf-8")
        styles = read_web_styles()

        self.assertNotIn('id="toggle-lang"', html)
        self.assertIn('id="open-help"', html)
        self.assertIn('class="btn-icon" id="open-settings"', html)
        self.assertIn('class="btn-icon" id="open-admin-panel"', html)
        self.assertNotIn('class="btn-icon admin-only" id="open-settings"', html)
        self.assertIn('id="settings-toggle-lang"', html)
        self.assertIn('id="settings-lang-label"', html)
        self.assertNotIn('id="settings-open-help"', html)
        self.assertIn("document.querySelectorAll('.lang-label')", ui_js)
        self.assertNotIn("document.querySelectorAll('.lang-label')", app_js)
        self.assertIn("width: min(430px, calc(100vw - 24px))", styles)
        self.assertIn(".modal--settings .modal-body", styles)
        self.assertIn("gap: 10px", styles)
        self.assertNotIn(".lang-switch", styles)
        self.assertNotIn(".draggable-modal.is-dragging {\n    animation: none;", styles)

    def test_all_modals_are_draggable_and_selects_show_dropdown_indicator(self):
        html = (ROOT_DIR / "web" / "index.html").read_text(encoding="utf-8")
        styles = read_web_styles()
        ui_js = (ROOT_DIR / "web" / "ui.js").read_text(encoding="utf-8")

        modal_dialogs = re.findall(r'class="modal(?:\s|")', html)
        draggable_dialogs = re.findall(r'class="modal[^"]*\bdraggable-modal\b', html)
        drag_handles = re.findall(r'class="modal-header[^"]*\bmodal-drag-handle\b', html)
        self.assertEqual(len(modal_dialogs), len(draggable_dialogs))
        self.assertEqual(len(modal_dialogs), len(drag_handles))
        self.assertIn("document.querySelectorAll('.draggable-modal .modal-drag-handle')", ui_js)
        self.assertIn("dialog.style.position = 'fixed'", ui_js)
        self.assertIn("function resetModalPosition(dialog)", ui_js)
        self.assertNotIn("function centerModalPosition(dialog)", ui_js)
        self.assertIn("function shouldCenterDraggableModals()", ui_js)
        self.assertIn("window.matchMedia('(max-width: 640px), (max-height: 520px)')", ui_js)
        self.assertIn("if (shouldCenterDraggableModals()) {\n        resetModalPosition(dialog);", ui_js)
        self.assertIn("if (shouldCenterDraggableModals()) return;", ui_js)
        self.assertIn("resetModalPosition(dialog);\n    if (saved && Number.isFinite(saved.left)", ui_js)
        self.assertIn("if (dialog.style.position !== 'fixed') return;", ui_js)
        self.assertIn(".modal-backdrop:not(.modal-backdrop--floating)", styles)
        self.assertIn(".modal-backdrop:not(.modal-backdrop--floating) .modal", styles)
        self.assertIn("max-height: calc(100dvh - 24px)", styles)
        self.assertIn(".modal--photo-review,\n    .modal--wreck-review,\n    .modal--privacy-requests", styles)
        self.assertIn("min-width: 0", styles)
        self.assertNotIn("requestAnimationFrame(() => centerModalPosition(dialog))", ui_js)
        self.assertIn(".modal--geotiff-cache {\n    position: absolute;", styles)
        self.assertIn("--select-chevron", styles)
        self.assertIn("select.modal-input", styles)
        self.assertIn("background-image: var(--select-chevron)", styles)

    def test_settings_modal_is_visible_with_locked_admin_controls_for_guests(self):
        html = (ROOT_DIR / "web" / "index.html").read_text(encoding="utf-8")
        app_js = read_web_app_scripts()
        admin_js = (ROOT_DIR / "web" / "admin.js").read_text(encoding="utf-8")
        i18n_js = (ROOT_DIR / "web" / "i18n.js").read_text(encoding="utf-8")
        styles = read_web_styles()

        self.assertIn('id="settings-lock-hint"', html)
        self.assertIn("function updateSettingsAccess()", app_js)
        self.assertIn("const adminSettingsControls = [", app_js)
        self.assertIn("settingsModal?.classList.toggle('settings-locked', locked)", app_js)
        self.assertIn("control.disabled = locked", app_js)
        self.assertIn("async function openSettingsModal()", admin_js)
        self.assertIn("async function openAdminPanel()", admin_js)
        self.assertNotIn("async function openSettingsModal()", app_js)
        self.assertNotIn("if (!(await ensureAdmin())) return;\n    openModal('modal-settings')", app_js)
        self.assertIn("'modal.settings.lockedHint': 'Log in as administrator to edit settings.'", i18n_js)
        self.assertIn(".settings-lock-hint", styles)
        self.assertIn(".modal--settings select:disabled", styles)

    def test_privacy_and_report_pages_have_english_i18n_coverage(self):
        index_html = (ROOT_DIR / "web" / "index.html").read_text(encoding="utf-8")
        privacy_html = (ROOT_DIR / "web" / "privacy.html").read_text(encoding="utf-8")
        report_html = (ROOT_DIR / "web" / "report.html").read_text(encoding="utf-8")
        i18n_js = (ROOT_DIR / "web" / "i18n.js").read_text(encoding="utf-8")

        self.assertIn("<title>WreckScanner</title>", index_html)
        self.assertIn("'meta.title': 'WreckScanner'", i18n_js)
        self.assertNotIn("Wrocław Ortho", index_html + i18n_js)
        self.assertNotIn("Pobierz dane dla AI", index_html + i18n_js)
        self.assertIn('data-i18n-title="page.privacy.title"', privacy_html)
        self.assertIn('data-i18n-description="page.privacy.description"', privacy_html)
        self.assertIn('data-i18n="page.privacy.intro"', privacy_html)
        self.assertIn('data-i18n="page.privacy.adminBody" data-i18n-html', privacy_html)
        self.assertIn('data-i18n="page.privacy.legalBody"', privacy_html)
        self.assertIn('data-i18n="page.privacy.scopeBody"', privacy_html)
        self.assertIn('data-i18n="page.privacy.requestsBody" data-i18n-html', privacy_html)
        self.assertIn('data-i18n="page.privacy.recipientsBody"', privacy_html)
        self.assertIn('data-i18n="page.privacy.rightsBody"', privacy_html)
        self.assertIn('data-i18n="page.privacy.complaintBody"', privacy_html)
        self.assertIn('data-i18n="page.privacy.logsBody"', privacy_html)
        self.assertIn('<script src="/i18n.js"></script>', privacy_html)
        self.assertIn('data-i18n-title="page.report.title"', report_html)
        self.assertIn('data-i18n-description="page.report.description"', report_html)
        self.assertIn('data-i18n="page.report.submit"', report_html)
        self.assertIn("status.textContent = t('page.report.sending')", report_html)
        self.assertIn('<script src="/i18n.js"></script>', report_html)
        self.assertIn("const titleKey = document.documentElement.dataset.i18nTitle || 'meta.title'", i18n_js)
        self.assertIn("'page.privacy.title': 'Privacy - WreckScanner'", i18n_js)
        self.assertIn("'page.privacy.adminTitle': 'Controller and contact'", i18n_js)
        self.assertIn("'page.privacy.complaintTitle': 'Complaint to UODO'", i18n_js)
        self.assertIn("'page.privacy.logsTitle': 'Technical logs'", i18n_js)
        self.assertIn("'page.report.title': 'Report a problem - WreckScanner'", i18n_js)
        self.assertIn("'page.report.saved': 'Request saved: {id}.'", i18n_js)
        self.assertIn("'modal.adminPanel.title': 'Administrator panel'", i18n_js)
        self.assertIn("'modal.adminPanel.publicLayers': 'Layers for signed-out users'", i18n_js)

    def test_readme_documents_photo_privacy_contract(self):
        readme_pl = (ROOT_DIR / "README.md").read_text(encoding="utf-8")

        self.assertIn("Publiczne API zwraca tylko `public_image` i `public_thumb`", readme_pl)
        self.assertIn("Oryginaly sa dostepne tylko przez endpointy administracyjne.", readme_pl)
        self.assertNotIn("web/photo", readme_pl)
        self.assertNotIn("Warstwa zdjęć terenowych, miniatury i oryginały są publicznie widoczne", readme_pl)

    def test_admin_login_and_delete_confirmation_use_app_modal_styles(self):
        html = (ROOT_DIR / "web" / "index.html").read_text(encoding="utf-8")
        admin_js = (ROOT_DIR / "web" / "admin.js").read_text(encoding="utf-8")
        ui_js = (ROOT_DIR / "web" / "ui.js").read_text(encoding="utf-8")
        i18n_js = (ROOT_DIR / "web" / "i18n.js").read_text(encoding="utf-8")
        styles = read_web_styles()

        self.assertIn('class="modal-input" id="admin-password-input"', html)
        self.assertIn('id="modal-confirm"', html)
        self.assertIn('id="confirm-message"', html)
        self.assertIn("function confirmAction", ui_js)
        self.assertIn("function openModal(id, options = {})", ui_js)
        self.assertIn("openModal('modal-confirm', { preserveOpen: true })", ui_js)
        self.assertIn("closeConfirmModal(false)", ui_js)
        self.assertIn("async function submitAdminLogin(event)", admin_js)
        self.assertNotIn("window.confirm", ui_js)
        self.assertIn(".modal-input", styles)
        self.assertIn("min-height: 42px", styles)
        self.assertIn(".modal-input:-webkit-autofill", styles)
        self.assertIn(".modal--confirm", styles)
        self.assertIn("#modal-confirm", styles)
        self.assertIn("z-index: 1200", styles)
        self.assertIn(".confirm-danger-btn", styles)
        self.assertIn("'modal.confirm.cancel': 'Anuluj'", i18n_js)
        self.assertIn("'fieldPhoto.deleteTitle': 'Delete field photos?'", i18n_js)
        self.assertIn("'wreck.deleteTitle': 'Delete vehicle case?'", i18n_js)

    def test_field_photo_upload_markup_and_limits_exist(self):
        sources = read_frontend_field_photo_contract_sources()
        html = sources["html"]
        app_js = sources["app_js"]
        config_js = sources["config_js"]

        self.assertIn('class="btn-icon" id="open-settings"', html)
        self.assertIn('id="open-field-photo-upload"', html)
        self.assertIn('class="admin-panel-action admin-only" id="open-field-photo-upload"', html)
        self.assertIn('id="modal-field-photo-upload"', html)
        self.assertIn('id="field-photo-issue-type"', html)
        self.assertIn('value="infrastructure"', html)
        self.assertIn('value="smoke"', html)
        self.assertIn('class="map-layer-controls is-loading-public-layers"', html)
        self.assertIn('id="field-photo-files"', html)
        self.assertIn('class="file-picker-input" id="field-photo-files"', html)
        self.assertIn('data-i18n="modal.fieldPhoto.chooseFiles"', html)
        self.assertIn('data-file-summary-for="field-photo-files"', html)
        self.assertIn('id="field-photo-ignore-exif"', html)
        self.assertIn('data-i18n="modal.fieldPhoto.ignoreExifGps"', html)
        self.assertIn('id="field-photo-queue"', html)
        self.assertIn('id="field-photo-retry"', html)
        self.assertIn('id="field-photo-edit-token"', html)
        self.assertIn('onclick="generateFieldPhotoEditToken()"', html)
        self.assertIn('onclick="copyFieldPhotoEditToken()"', html)
        self.assertIn('id="modal-field-photo-thanks"', html)
        self.assertIn('id="field-photo-thanks-token"', html)
        self.assertIn('onclick="copyFieldPhotoThanksToken()"', html)
        self.assertIn('id="modal-field-photo-owner"', html)
        self.assertIn('class="btn-download report-submit-btn field-photo-owner-submit"', html)
        self.assertIn('onsubmit="submitFieldPhotoOwnerToken(event)"', html)
        self.assertIn("const FIELD_PHOTOS_URL = '/api/field-photos'", config_js)
        self.assertIn("const FIELD_PHOTO_MAX_BYTES = 10 * 1024 * 1024", config_js)
        self.assertIn("const FIELD_PHOTO_MAX_FILES = 25", config_js)
        self.assertIn("const FIELD_PHOTO_EDIT_TOKEN_MIN_LENGTH = 8", config_js)
        self.assertIn("const FIELD_PHOTO_EDIT_TOKEN_MAX_LENGTH = 80", config_js)
        self.assertIn("const FIELD_PHOTO_ISSUE_TYPE_VEHICLE = 'vehicle'", config_js)
        self.assertIn("const FIELD_PHOTO_ISSUE_TYPES = new Set", config_js)
        self.assertIn("const FIELD_PHOTO_GROUP_RADIUS_M = 1", config_js)
        self.assertNotIn("const FIELD_PHOTO_GROUP_RADIUS_M", app_js)

    def test_field_photo_upload_queue_and_token_flow_exists(self):
        sources = read_frontend_field_photo_contract_sources()
        app_js = sources["app_js"]

        self.assertIn("let fieldPhotoUploadItems = []", app_js)
        self.assertIn("let fieldPhotoMarkers = []", app_js)
        self.assertIn("const issueSelect = document.getElementById('field-photo-issue-type')", app_js)
        self.assertIn("if (issueSelect) issueSelect.value = requestedIssueType", app_js)
        self.assertIn("function loadFieldPhotos()", app_js)
        self.assertIn("function deleteFieldPhoto", app_js)
        self.assertIn("function uploadFieldPhotoItems(items)", app_js)
        self.assertIn("function retryFailedFieldPhotoUploads()", app_js)
        self.assertIn("if (!publicFeatureAllowed(PUBLIC_FEATURE_KEYS.photoUploads)) return;", app_js)
        self.assertIn("function updateFilePickerSummary(input)", app_js)
        self.assertIn("document.querySelectorAll('.file-picker-input')", app_js)
        self.assertIn("document.addEventListener('langchange', updateAllFilePickerSummaries)", app_js)
        self.assertIn("validationError: Boolean(error)", app_js)
        self.assertIn("formData.append('ignore_exif_gps', item.ignoreExifGps ? '1' : '0')", app_js)
        self.assertIn("formData.append('issue_type', item.issueType || FIELD_PHOTO_ISSUE_TYPE_VEHICLE)", app_js)
        self.assertIn("formData.append('edit_token', item.editToken)", app_js)
        self.assertIn("item.photo = data.photo || null", app_js)
        self.assertNotIn("lat: data.photo?.lat", app_js)
        self.assertNotIn("kind: 'photo'", app_js)
        self.assertIn("closeModal(document.getElementById('modal-field-photo-upload'))", app_js)
        self.assertIn("function openFieldPhotoThanksModal({ saved = 0, editToken = '' } = {})", app_js)
        self.assertIn("function copyFieldPhotoThanksToken()", app_js)
        self.assertIn("const submittedEditToken = adminAuthenticated", app_js)
        self.assertIn("openFieldPhotoThanksModal({ saved: summary.saved, editToken: submittedEditToken })", app_js)
        self.assertIn("item.ignoreExifGps = ignoreExifGps", app_js)
        self.assertIn("item.issueType = issueType", app_js)
        self.assertIn("t('modal.fieldPhoto.queueSubmittedForReview')", app_js)
        self.assertIn("t('modal.fieldPhoto.submittedForReview', { n: summary.saved })", app_js)
        self.assertIn("fieldPhotoUploadItems.filter(item => item.status === 'pending')", app_js)

    def test_field_photo_map_grouping_and_review_gates_exist(self):
        sources = read_frontend_field_photo_contract_sources()
        app_js = sources["app_js"]

        self.assertIn("function fieldPhotoIssueType(photo)", app_js)
        self.assertIn("function fieldPhotoIssueAllowed(issueType)", app_js)
        self.assertIn("function fieldPhotoReviewStatus(photo)", app_js)
        self.assertIn("function fieldPhotoGroupKind(photo)", app_js)
        self.assertIn("function pendingFieldPhotoPopup(group)", app_js)
        self.assertIn("function fieldPhotoPendingReviewPopup(group)", app_js)
        self.assertIn("function rejectFieldPhotoGroup(encodedPhotoIds, button = null)", app_js)
        self.assertIn("fieldPhotoReviewStatus(photo) === 'approved'", app_js)
        self.assertIn("function updateFieldPhotoIssueOptions()", app_js)
        self.assertIn("const enabled = fieldPhotoIssueAllowed(issueType)", app_js)
        self.assertIn("option.disabled = !enabled", app_js)
        self.assertIn("option.hidden = !enabled", app_js)
        self.assertIn("if (!fieldPhotoIssueAllowed(issueType))", app_js)
        self.assertIn("t('modal.fieldPhoto.issueTypeUnavailable')", app_js)
        self.assertIn("function filteredFieldPhotos(photos = fieldPhotoLayerData)", app_js)
        self.assertIn("candidate.issueType === issueType", app_js)
        self.assertIn("function groupFieldPhotos(photos)", app_js)
        self.assertIn("pendingSubmissionIcon('photo')", app_js)
        self.assertIn("fieldPhotoIcon(group.photos.length, group.issueType)", app_js)
        self.assertIn("fieldPhotoGroupPopup(group)", app_js)
        self.assertIn("draggable: adminAuthenticated", app_js)
        self.assertIn("marker.on('dragend', () => updateFieldPhotoGroupLocation(group, marker))", app_js)

    def test_field_photo_group_actions_report_owner_review_and_attachment_exist(self):
        sources = read_frontend_field_photo_contract_sources()
        app_js = sources["app_js"]

        self.assertIn("function updateFieldPhotoLocation(photo, lat, lon)", app_js)
        self.assertIn("function nearestWreckForAttachment(lat, lon)", app_js)
        self.assertIn("function attachFieldPhotoGroupToWreck(group, wreck)", app_js)
        self.assertIn("function createWreckForFieldPhotoGroup(lat, lon, encodedPhotoIds)", app_js)
        self.assertIn("function createManualWreckForFieldPhotoGroup(lat, lon)", app_js)
        self.assertIn("function fieldPhotosForReport(encodedPhotoIds)", app_js)
        self.assertIn("function openFieldPhotoGroupReport(lat, lon, encodedPhotoIds, button = null)", app_js)
        self.assertIn(
            "function openFieldPhotoGroupPhotoUpload(lat, lon, encodedPhotoIds, issueType = FIELD_PHOTO_ISSUE_TYPE_VEHICLE, button = null)",
            app_js,
        )
        self.assertIn("function openPhotoReviewForFieldPhotoGroup(encodedPhotoIds)", app_js)
        self.assertIn("function openFieldPhotoOwnerEditor(encodedPhotoIds)", app_js)
        self.assertIn("function submitFieldPhotoOwnerToken(event)", app_js)
        self.assertIn("const data = await apiPostJson(`${FIELD_PHOTOS_URL}/owner-claim`", app_js)
        self.assertIn("function photoReviewOriginalImageSrc(item)", app_js)
        self.assertIn("body: JSON.stringify({ edit_token: ownerPhotoReviewToken })", app_js)
        self.assertIn("`${FIELD_PHOTOS_URL}/${encodeURIComponent(item.photo_id)}/owner-review`", app_js)
        self.assertIn("function deleteFieldPhotoGroup(encodedPhotoIds, button = null)", app_js)
        self.assertIn("openFieldPhotoGroupReport(", app_js)
        self.assertIn("openFieldPhotoGroupPhotoUpload(", app_js)
        self.assertIn("openPhotoReviewForFieldPhotoGroup('", app_js)
        self.assertIn("openFieldPhotoOwnerEditor('", app_js)
        self.assertIn("photoReviewExactPhotoIds.join(',')", app_js)
        self.assertIn("deleteFieldPhotoGroup(", app_js)
        self.assertIn("fieldPhotoGroupActions({ ...group, issueType })", app_js)
        self.assertIn(
            "openReportPackageModal(wreckId, { extraPhotos: adminAuthenticated ? [] : fieldPhotosForReport(encodedPhotoIds) })",
            app_js,
        )
        self.assertIn("function appendReportPackageExtraPhotos(formData)", app_js)
        self.assertIn("formData.append('photos[]', blob, photo.filename || 'zdjecie_terenowe.jpg')", app_js)
        self.assertIn("const reportPhotoFiles = publicFeatureAllowed(PUBLIC_FEATURE_KEYS.photoUploads)", app_js)
        self.assertIn("validateReportPackageFiles(reportPhotoFiles, reportPackageExtraPhotos.length)", app_js)
        self.assertIn("if (typeof refreshAdminStatus === 'function') await refreshAdminStatus();", app_js)
        self.assertIn("field-photos/attach", app_js)
        self.assertNotIn("field-photos/link", app_js)
        self.assertIn("FIELD_PHOTO_ATTACH_TO_WRECK_RADIUS_M", app_js)
        self.assertIn("group.issueType === FIELD_PHOTO_ISSUE_TYPE_VEHICLE", app_js)
        self.assertIn("method: 'PATCH'", app_js)
        self.assertIn("await loadFieldPhotos();", app_js)
        self.assertIn("await loadSavedWrecks();", app_js)
        self.assertIn("loadFieldPhotos();", app_js)
        self.assertNotIn("t('fieldPhoto.moveTitle')", app_js)
        self.assertNotIn("t('fieldPhoto.attachToWreckTitle')", app_js)
        self.assertNotIn("async function deleteFieldPhoto(photoId, button = null)", app_js)
        self.assertNotIn("if (!adminAuthenticated) return;\n    groupFieldPhotos(photos)", app_js)
        self.assertNotIn("if (!adminAuthenticated) {\n        clearFieldPhotoMarkers();", app_js)

    def test_field_photo_i18n_and_styles_exist(self):
        sources = read_frontend_field_photo_contract_sources()
        app_js = sources["app_js"]
        i18n_js = sources["i18n_js"]
        styles = sources["styles"]

        self.assertIn("'icon.settings': 'Ustawienia'", i18n_js)
        self.assertIn("'icon.fieldPhotoUpload': 'Dodaj zdjęcia terenowe'", i18n_js)
        self.assertIn("'modal.fieldPhoto.title': 'Zdjęcia terenowe'", i18n_js)
        self.assertIn("'modal.fieldPhoto.issueType': 'Typ miejsca'", i18n_js)
        self.assertIn("'modal.fieldPhoto.chooseFiles': 'Wybierz zdjęcia z terenu'", i18n_js)
        self.assertIn("'modal.fieldPhoto.submit': 'Dodaj na mapę'", i18n_js)
        self.assertIn("'modal.fieldPhoto.submit': 'Add to map'", i18n_js)
        self.assertIn("'modal.fieldPhotoThanks.title': 'Dziękujemy za zdjęcie'", i18n_js)
        self.assertIn("'modal.fieldPhotoThanks.summaryOne': 'Zdjęcie trafiło do weryfikacji.'", i18n_js)
        self.assertIn(
            "'modal.fieldPhotoThanks.stepApproval': 'Administrator zatwierdzi zdjęcie przed publikacją.'", i18n_js
        )
        self.assertIn("'modal.fieldPhotoThanks.title': 'Thanks for the photo'", i18n_js)
        self.assertIn("'fieldPhoto.issueType.infrastructure': 'Niebezpieczna infrastruktura'", i18n_js)
        self.assertIn("'fieldPhoto.issueType.smoke': 'Zanieczyszczone powietrze'", i18n_js)
        self.assertIn("'fieldPhoto.issueType.smoke': 'Polluted air'", i18n_js)
        self.assertIn(
            "'modal.fieldPhoto.issueTypeUnavailable': 'Ta kategoria jest wyłączona w warstwach mapy.'", i18n_js
        )
        self.assertIn("'modal.fieldPhoto.ignoreExifGps': 'Ignoruj GPS z EXIF i użyj punktu mapy'", i18n_js)
        self.assertNotIn("'fieldPhoto.moveTitle'", i18n_js)
        self.assertNotIn("'fieldPhoto.attachToWreckTitle'", i18n_js)
        self.assertIn("'fieldPhoto.attachToWreckSaving': 'Przenoszę zdjęcia do sprawy pojazdu: {n}...'", i18n_js)
        self.assertIn("'fieldPhoto.attachToWreckSaved': 'Moved photos to vehicle case: {n}.'", i18n_js)
        self.assertIn("'fieldPhoto.reportPackage': 'Generuj zgłoszenie do weryfikacji'", i18n_js)
        self.assertIn("'fieldPhoto.reviewPhotos': 'Edytuj anonimizację zdjęć'", i18n_js)
        self.assertIn("'fieldPhoto.addPhotosHere': 'Dodaj kolejne zdjęcia tutaj'", i18n_js)
        self.assertIn("'fieldPhoto.addPhotosHere': 'Add more photos here'", i18n_js)
        self.assertIn("'fieldPhoto.pendingReview.title': 'Zdjęcie do weryfikacji'", i18n_js)
        self.assertIn("'fieldPhoto.pendingReview.title': 'Photo for review'", i18n_js)
        self.assertIn("'fieldPhoto.rejectError': 'Nie udało się odrzucić zdjęcia terenowego.'", i18n_js)
        self.assertNotIn("fieldPhoto.addPhotosToCase", i18n_js)
        self.assertIn("'fieldPhoto.reviewPhotos': 'Edit photo anonymization'", i18n_js)
        self.assertIn("'fieldPhoto.prepareCaseSaving': 'Przygotowuję sprawę pojazdu...'", i18n_js)
        self.assertIn(
            "'modal.report.extraPublicPhotos': 'Dołączę publiczne zanonimizowane zdjęcia z mapy: {n}.'", i18n_js
        )
        self.assertIn("'modal.report.extraPublicPhotosError': 'Could not attach public map photos.'", i18n_js)
        self.assertIn("'modal.fieldPhoto.fileCountError': 'Choose up to {n} photos at a time.'", i18n_js)
        self.assertIn("'modal.fieldPhoto.retryFailed': 'Retry failed'", i18n_js)
        self.assertIn(
            "'modal.fieldPhoto.uploadSummaryWithErrors': 'Finished: saved {saved}/{total}, errors: {failed}.'", i18n_js
        )
        self.assertIn("'fieldPhoto.source.manual': 'moved manually'", i18n_js)
        self.assertIn("'fieldPhoto.locationUpdated': 'Updated photo position: {n}.'", i18n_js)
        self.assertIn("'fieldPhoto.popup.title': 'Field photo'", i18n_js)
        self.assertIn("'fieldPhoto.popup.groupTitle': 'Field photos: {n}'", i18n_js)
        self.assertIn("width: 300px", styles)
        self.assertIn(".modal--field-photo-thanks", styles)
        self.assertIn(".field-photo-owner-submit", styles)
        self.assertIn("flex: 0 0 auto;", styles[styles.index(".field-photo-owner-submit") :])
        self.assertIn(".field-photo-toggle", styles)
        self.assertIn(".field-photo-pin", styles)
        self.assertIn(".layer-pin--field-photo-infrastructure", styles)
        self.assertIn(".layer-pin--field-photo-smoke", styles)
        self.assertIn(".field-photo-pin--infrastructure", styles)
        self.assertIn(".field-photo-pin--smoke", styles)
        self.assertIn(".leaflet-marker-draggable .field-photo-pin", styles)
        self.assertIn("field-photo-pin-count", app_js)
        self.assertIn("saved-wreck-pin-count", app_js)
        self.assertIn(".map-pin-count", styles)
        self.assertIn(".field-photo-queue", styles)
        self.assertIn(".field-photo-retry-btn", styles)
        self.assertIn(".file-picker-button", styles)
        self.assertIn(".file-picker-summary", styles)
        self.assertIn(".map-popup-photo-grid", styles)
        self.assertIn(".modal--photo-preview", styles)
        self.assertIn(".photo-preview-frame", styles)
        self.assertIn(".photo-preview-controls", styles)
        self.assertIn(".photo-preview-nav", styles)
        self.assertIn(".photo-review-detail", styles)
        self.assertIn(".map-popup-action", styles)
        self.assertIn(".map-popup-text-action", styles)
        self.assertNotIn(".map-popup-card-grid", styles)
        self.assertNotIn(".map-popup-thumb", styles)
        self.assertNotIn(".field-photo-popup-grid", styles)
        self.assertNotIn(".wreck-popup-previews", styles)
        self.assertNotIn(".wreck-popup-preview-download", styles)
        self.assertNotIn(".popup-report-btn", styles)

    def test_map_layer_panel_toggles_and_loading_state_exist(self):
        sources = read_frontend_map_layer_contract_sources()
        html = sources["html"]
        app_js = sources["app_js"]
        styles = sources["styles"]

        self.assertIn('id="map-layer-controls"', html)
        self.assertIn('class="panel-section panel-layers"', html)
        self.assertIn('id="toggle-saved-wrecks"', html)
        self.assertIn('onchange="toggleSavedWreckLayer(this.checked)"', html)
        self.assertIn('id="toggle-cadastral-parcels"', html)
        self.assertIn('onchange="toggleCadastralLayer(this.checked)"', html)
        self.assertIn('id="toggle-surface-layer"', html)
        self.assertIn('onchange="setSurfaceLayerVisible(this.checked)"', html)
        self.assertIn('id="surface-layer-status"', html)
        self.assertIn('id="toggle-field-photo-vehicle"', html)
        self.assertIn('id="toggle-field-photo-infrastructure"', html)
        self.assertIn('id="toggle-field-photo-smoke"', html)
        self.assertIn('id="toggle-field-photo-pending"', html)
        self.assertIn("toggleFieldPhotoIssueFilter('vehicle', this.checked)", html)
        self.assertIn("toggleFieldPhotoIssueFilter('infrastructure', this.checked)", html)
        self.assertIn("toggleFieldPhotoIssueFilter('smoke', this.checked)", html)
        self.assertIn("togglePendingFieldPhotoLayer(this.checked)", html)
        self.assertIn('data-i18n="layers.savedWrecks"', html)
        self.assertIn('data-i18n="layers.cadastral"', html)
        self.assertIn('data-i18n-attr="title:layers.cadastralTooltip"', html)
        self.assertIn('data-i18n="layers.surface"', html)
        self.assertIn('data-i18n="layers.fieldPhotoVehicles"', html)
        self.assertIn('data-i18n="layers.fieldPhotoInfrastructure"', html)
        self.assertIn('data-i18n="layers.fieldPhotoSmoke"', html)
        self.assertIn('data-i18n="layers.fieldPhotoPending"', html)
        self.assertIn("let publicLayerSettingsLoaded = false", app_js)
        self.assertIn("'is-loading-public-layers'", app_js)
        self.assertIn(".map-layer-controls.is-loading-public-layers .layer-toggle", styles)
        self.assertIn("let savedWreckLayerData = []", app_js)
        self.assertIn("let fieldPhotoLayerData = []", app_js)
        self.assertIn("let pendingSubmissionLayer = L.layerGroup().addTo(map)", app_js)
        self.assertIn("function addPendingSubmissionMarker({ lat, lon } = {})", app_js)
        self.assertIn("function clearPendingSubmissionMarkers()", app_js)
        settings_access_slice = app_js[
            app_js.index("function updateSettingsAccess()") : app_js.index("function normalizePublicLayerSettings")
        ]
        self.assertNotIn("clearPendingSubmissionMarkers()", settings_access_slice)
        self.assertIn("let savedWreckLayerVisible = true", app_js)
        self.assertIn("let cadastralLayerVisible = false", app_js)
        self.assertIn("let surfaceLayerVisible = false", app_js)
        self.assertIn("let fieldPhotoIssueFilters = Object.fromEntries", app_js)

    def test_map_layer_surface_and_cadastral_contracts_exist(self):
        sources = read_frontend_map_layer_contract_sources()
        app_js = sources["app_js"]
        config_js = sources["config_js"]

        self.assertNotIn("surfaceRasterPane", app_js)
        self.assertIn("const surfacePane = map.createPane('surfacePane')", app_js)
        self.assertIn("surfacePane.style.zIndex = 450", app_js)
        self.assertIn("const CADASTRAL_LAYER_VISIBLE_STORAGE_KEY", config_js)
        self.assertNotIn("SURFACE_LAYER_VISIBLE_STORAGE_KEY", config_js)
        self.assertNotIn("SURFACE_LAYER_VISIBLE_STORAGE_KEY", app_js)
        self.assertNotIn("wroclaw-ortho-surface-visible", config_js + app_js)
        self.assertIn("const SURFACE_FEATURES_URL = '/api/surface/features'", config_js)
        self.assertNotIn("SURFACE_OVERPASS_URL", config_js)
        self.assertIn(
            "const CADASTRAL_WMS_URL = 'https://integracja.gugik.gov.pl/cgi-bin/KrajowaIntegracjaEwidencjiGruntow'",
            config_js,
        )
        self.assertIn("const CADASTRAL_WMS_LAYERS = 'dzialki,numery_dzialek'", config_js)
        self.assertIn("function buildCadastralLayer()", app_js)
        self.assertIn("function setCadastralLayerVisible(visible)", app_js)
        self.assertIn("publicLayerAllowed(PUBLIC_LAYER_KEYS.cadastral)", app_js)
        self.assertIn("const contextIdentifyParcelButton = document.getElementById('context-identify-parcel')", app_js)
        self.assertIn("contextIdentifyParcelButton.hidden = !publicLayerAllowed(PUBLIC_LAYER_KEYS.cadastral)", app_js)
        self.assertIn("publicLayerAllowed(PUBLIC_LAYER_KEYS.surface)", app_js)
        self.assertIn("function loadSurfaceLayer()", app_js)
        self.assertIn("function setSurfaceLayerVisible(visible)", app_js)
        self.assertIn("function scheduleSurfaceLayerLoad(delayMs = 650)", app_js)
        self.assertNotIn("function setSurfaceFallbackLayerVisible", app_js)
        self.assertIn("url: OSM_TILE_URL", config_js)
        self.assertIn("maxNativeZoom: 19", config_js)
        self.assertIn("maxNativeZoom: source.maxNativeZoom || MAX_MAP_ZOOM", app_js)
        self.assertIn("function setSurfaceLayerStatus(key = '', params = {}, state = '')", app_js)
        self.assertIn("function surfaceKindLabel(kind)", app_js)
        self.assertIn("function surfaceTagLabel(group, value)", app_js)
        self.assertIn("function surfacePopupRow(labelKey, value)", app_js)
        self.assertIn('class="map-popup map-popup--surface"', app_js)
        self.assertIn("surfacePopupRow('layers.surfacePopup.kind', surfaceKindLabel(props.kind))", app_js)
        self.assertIn("pane: 'surfacePane'", app_js)
        self.assertNotIn("pane: 'surfaceRasterPane'", app_js)
        self.assertIn("function toggleCadastralLayer(visible)", app_js)
        self.assertIn("layers: CADASTRAL_WMS_LAYERS", app_js)
        self.assertIn("styles: 'default,default'", app_js)
        self.assertIn("transparent: true", app_js)
        self.assertIn("localStorage.setItem(CADASTRAL_LAYER_VISIBLE_STORAGE_KEY", app_js)
        self.assertIn("function toggleSavedWreckLayer(visible)", app_js)

    def test_map_layer_public_access_and_feature_gates_exist(self):
        sources = read_frontend_map_layer_contract_sources()
        html = sources["html"]
        app_js = sources["app_js"]
        config_js = sources["config_js"]

        self.assertIn("const PUBLIC_LAYER_KEYS = {", config_js)
        self.assertIn("const PUBLIC_FEATURE_KEYS = {", config_js)
        self.assertIn("scanAnalysis: 'scan_analysis'", config_js)
        self.assertIn("yoloWrecks: 'yolo_wrecks'", config_js)
        self.assertIn("manualWrecks: 'manual_wrecks'", config_js)
        self.assertIn("photoUploads: 'photo_uploads'", config_js)
        self.assertIn("baseMapOsm: 'base_map_osm'", config_js)
        self.assertIn("cadastral: 'cadastral'", config_js)
        self.assertIn("surface: 'surface'", config_js)
        self.assertIn("fieldPhotoPending: 'field_photo_pending'", config_js)
        self.assertIn("const FIELD_PHOTO_PUBLIC_LAYER_KEYS = {", config_js)
        self.assertIn("let publicLayerSettings = Object.fromEntries", app_js)
        self.assertIn("if (!publicLayerSettingsLoaded) return false;", app_js)
        self.assertIn("function savePublicLayerSettings()", app_js)
        self.assertIn("function publicLayerAllowed(layerKey)", app_js)
        self.assertIn("let publicFeatureSettings = Object.fromEntries", app_js)
        self.assertIn("let publicFeatureSettingsLoaded = false", app_js)
        self.assertIn("function savePublicFeatureSettings()", app_js)
        self.assertIn("function publicFeatureAllowed(featureKey)", app_js)
        self.assertIn("if (!publicFeatureSettingsLoaded) return false;", app_js)
        self.assertIn("publicFeatureSettingsLoaded = true;\n        updatePublicLayerAccess();", app_js)
        self.assertIn('id="btn-run" onclick="runAll()" hidden', html)
        self.assertIn('id="report-photos-section" hidden', html)
        self.assertIn("runButton.hidden = !scanAllowed", app_js)
        self.assertIn("const yoloWrecksAllowed = publicFeatureAllowed(PUBLIC_FEATURE_KEYS.yoloWrecks)", app_js)
        self.assertIn("data-yolo-wreck-save", app_js)
        self.assertIn("if (!publicFeatureAllowed(PUBLIC_FEATURE_KEYS.yoloWrecks))", app_js)
        self.assertIn("const contextCenterScanButton = document.getElementById('context-center-scan')", app_js)
        self.assertIn("contextCenterScanButton.hidden = !scanAllowed", app_js)
        self.assertIn("contextCrosshairButton.hidden = !scanAllowed", app_js)
        self.assertIn("if (crosshairVisibilityControllerReady) updateCrosshairVisibility();", app_js)
        self.assertIn("const contextFieldPhotoButton = document.getElementById('context-add-field-photos')", app_js)
        self.assertIn("const fieldPhotoUploadAvailable = photoUploadsAllowed && fieldPhotoAnyIssueAllowed()", app_js)
        self.assertIn("contextFieldPhotoButton.hidden = !fieldPhotoUploadAvailable", app_js)
        self.assertIn("panelPhotoUploadButton.hidden = !fieldPhotoUploadAvailable", app_js)
        self.assertIn("const manualWrecksAllowed = publicFeatureAllowed(PUBLIC_FEATURE_KEYS.manualWrecks)", app_js)
        self.assertIn("const canAddFieldPhotosHere = coordinatesOk", app_js)
        self.assertIn("&& publicFeatureAllowed(PUBLIC_FEATURE_KEYS.photoUploads)", app_js)
        self.assertIn("&& fieldPhotoIssueAllowed(issueType)", app_js)
        self.assertIn("const photoButton = canAddFieldPhotosHere", app_js)
        self.assertIn("if (!publicFeatureAllowed(PUBLIC_FEATURE_KEYS.manualWrecks)) return null;", app_js)
        self.assertIn("if (!publicFeatureAllowed(PUBLIC_FEATURE_KEYS.manualWrecks)) return;", app_js)
        self.assertIn("await openFieldPhotoUploadModal({", app_js)

    def test_map_layer_field_photo_filters_and_counters_exist(self):
        sources = read_frontend_map_layer_contract_sources()
        app_js = sources["app_js"]

        self.assertIn("function toggleFieldPhotoIssueFilter(issueType, visible)", app_js)
        self.assertIn("function togglePendingFieldPhotoLayer(visible)", app_js)
        self.assertIn("fieldPhotoIssueFilters[safeIssueType] = Boolean(visible)", app_js)
        self.assertIn("let pendingFieldPhotoLayerVisible = true", app_js)
        self.assertIn("publicLayerAllowed(PUBLIC_LAYER_KEYS.fieldPhotoPending)", app_js)
        self.assertIn("groupFieldPhotos(filteredFieldPhotos(photos)).forEach", app_js)
        self.assertIn("function countLingeringCars()", app_js)
        self.assertIn("function updateLingeringCarsCounter()", app_js)
        self.assertIn("Number(wreck.photo_count) > 0", app_js)
        self.assertIn("const vehiclePhotos = publicLayerAllowed(PUBLIC_LAYER_KEYS.fieldPhotoVehicle)", app_js)
        self.assertIn("groupFieldPhotos(vehiclePhotos).length", app_js)
        self.assertIn("document.addEventListener('langchange', updateLingeringCarsCounter)", app_js)
        self.assertIn(
            "if (!savedWreckLayerVisible || !publicLayerAllowed(PUBLIC_LAYER_KEYS.savedWrecks)) return;", app_js
        )
        self.assertNotIn("fieldPhotoLayerVisible", app_js)
        self.assertNotIn("toggleFieldPhotoLayer", app_js)
        self.assertIn("savedWreckLayerData = data.wrecks || []", app_js)
        self.assertIn("fieldPhotoLayerData = data.photos || []", app_js)

    def test_map_layer_manual_wreck_and_inspection_contracts_exist(self):
        sources = read_frontend_map_layer_contract_sources()
        app_js = sources["app_js"]

        self.assertIn("function saveManualWreck(lat, lon, button = null)", app_js)
        self.assertIn("function selectedReviewCropM()", app_js)
        self.assertIn("addPendingSubmissionMarker({ lat: data.wreck?.lat", app_js)
        self.assertIn("addPendingSubmissionMarker({ lat: data.wreck?.lat ?? latNumber", app_js)
        self.assertIn("t('inspect.submittedWreck')", app_js)
        self.assertIn("const data = await apiPostJson(WRECKS_URL, { lat: latNumber, lon: lonNumber, cropM })", app_js)
        self.assertIn("const data = await apiPostJson('/api/inspect'", app_js)
        self.assertIn("saveManualWreck(${inspectLat.toFixed(8)}, ${inspectLon.toFixed(8)}, this)", app_js)

    def test_map_layer_i18n_and_styles_exist(self):
        sources = read_frontend_map_layer_contract_sources()
        i18n_js = sources["i18n_js"]
        styles = sources["styles"]

        self.assertIn("'layers.savedWrecks': 'Sprawy pojazdów'", i18n_js)
        self.assertIn("'layers.cadastral': 'Granice działek'", i18n_js)
        self.assertIn(
            "'layers.cadastralTooltip': 'Działki ewidencyjne KIEG/GUGiK: granice i numery działek, bez danych właścicieli.'",
            i18n_js,
        )
        self.assertIn("'layers.surface': 'Nawierzchnia'", i18n_js)
        self.assertIn("'layers.surfaceLoading': 'ładuję...'", i18n_js)
        self.assertNotIn("'layers.surfaceRasterFallback'", i18n_js)
        self.assertIn("'layers.baseMapOsm': 'Mapa OSM'", i18n_js)
        self.assertIn("'layers.surfacePopup.kind': 'Rodzaj'", i18n_js)
        self.assertIn("'layers.surfaceKind.sidewalk': 'chodnik / ciąg pieszy'", i18n_js)
        self.assertIn("'layers.surfaceHighway.service': 'droga wewnętrzna / dojazdowa'", i18n_js)
        self.assertIn("'layers.surfaceMaterial.paving_stones': 'kostka brukowa'", i18n_js)
        self.assertIn("'layers.surfaceKerb.lowered': 'obniżony'", i18n_js)
        self.assertIn("'layers.surfacePopup.kind': 'Type'", i18n_js)
        self.assertIn("'layers.fieldPhotoVehicles': 'Zdjęcia pojazdów'", i18n_js)
        self.assertIn("'layers.fieldPhotoInfrastructure': 'Niebezpieczna infrastruktura'", i18n_js)
        self.assertIn("'layers.fieldPhotoSmoke': 'Zanieczyszczone powietrze'", i18n_js)
        self.assertIn("'layers.fieldPhotoPending': 'Do weryfikacji'", i18n_js)
        self.assertIn(
            "'pendingSubmission.reviewHint': 'Czeka na zatwierdzenie administratora. Ten znacznik jest widoczny tylko lokalnie.'",
            i18n_js,
        )
        self.assertIn("'fieldPhoto.pendingPublicHint': 'Czeka na zatwierdzenie administratora.'", i18n_js)
        self.assertIn("'modal.fieldPhoto.submittedForReview': 'Zdjęcia wysłane do weryfikacji: {n}.'", i18n_js)
        self.assertIn(
            "'wreck.submittedForReview': 'Zgłoszenie zapisane i czeka na zatwierdzenie administratora.'", i18n_js
        )
        self.assertIn(".pending-submission-pin", styles)
        self.assertNotIn(".map-popup-thumb--pending", styles)
        self.assertIn("'layers.fieldPhotoSmoke': 'Polluted air'", i18n_js)
        self.assertIn("'layers.fieldPhotoVehicles': 'Vehicle photos'", i18n_js)
        self.assertIn("'layers.fieldPhotoPending': 'For review'", i18n_js)
        self.assertIn("'layers.cadastral': 'Parcel boundaries'", i18n_js)
        self.assertIn("'layers.baseMapOsm': 'OSM map'", i18n_js)
        self.assertIn("'layers.title': 'Warstwy'", i18n_js)
        self.assertIn("'inspect.saveWreck': 'Dodaj z wycinkiem'", i18n_js)
        self.assertIn("'inspect.saveWreck': 'Add with crop'", i18n_js)
        self.assertIn(".map-layer-controls", styles)
        self.assertNotIn("right: 16px;\n    bottom: 96px", styles)
        self.assertIn(".layer-toggle input:checked::after", styles)
        self.assertIn(".layer-pin--wreck", styles)
        self.assertIn(".layer-pin--cadastral", styles)
        self.assertIn(".layer-pin--surface", styles)
        self.assertIn(".layer-pin--base-map-osm", styles)
        self.assertIn(".layer-status.is-error", styles)
        self.assertIn(".map-popup--surface", styles)
        self.assertIn(".surface-popup-row", styles)
        self.assertIn(".layer-pin--field-photo-vehicle", styles)
        self.assertIn(".layer-pin--field-photo-infrastructure", styles)
        self.assertIn(".layer-pin--field-photo-smoke", styles)

    def test_scan_area_controls_context_menu_and_crosshair_contract(self):
        html = (ROOT_DIR / "web" / "index.html").read_text(encoding="utf-8")
        app_main_js = (ROOT_DIR / "web" / "app.js").read_text(encoding="utf-8")
        scan_area_js = (ROOT_DIR / "web" / "app" / "scan_area.js").read_text(encoding="utf-8")
        scan_progress_js = (ROOT_DIR / "web" / "app" / "scan_progress.js").read_text(encoding="utf-8")
        app_js = read_web_app_scripts()
        config_js = (ROOT_DIR / "web" / "config.js").read_text(encoding="utf-8")
        i18n_js = (ROOT_DIR / "web" / "i18n.js").read_text(encoding="utf-8")
        styles = read_web_styles()

        self.assertIn('data-i18n="modal.settings.scanArea"', html)
        self.assertIn('id="width-slider" min="50" max="50"', html)
        self.assertIn("const SCAN_AREA_MIN_M = 50", config_js)
        self.assertIn("const SCAN_AREA_MAX_M = 50", config_js)
        self.assertIn("const CROSSHAIR_MAX_VIEWPORT_RATIO = 0.82", config_js)
        self.assertIn("const CROSSHAIR_HIDDEN_STORAGE_KEY = 'wroclaw-ortho-crosshair-hidden'", config_js)
        self.assertIn("const FIELD_PHOTO_ATTACH_TO_WRECK_RADIUS_M = 1", config_js)
        self.assertIn("const MARKER_DETAIL_FULL_MIN_ZOOM = 18", config_js)
        self.assertIn("const MARKER_DETAIL_DOT_MAX_ZOOM = 16", config_js)
        self.assertIn('id="crosshair" class="is-hidden"', html)
        self.assertIn("function clampScanSize(value)", app_js)
        self.assertIn("function clampScanSize(value)", scan_area_js)
        self.assertNotIn("function clampScanSize(value)", app_main_js)
        self.assertIn("widthSlider.hidden = SCAN_AREA_MIN_M === SCAN_AREA_MAX_M", app_js)
        self.assertIn("const snap = clampScanSize", app_js)
        self.assertIn("const snap = clampScanSize", scan_area_js)
        self.assertNotIn("const snap = clampScanSize", app_main_js)
        self.assertIn("sizeLabel.textContent = `${currentWidth} \\u00d7 ${currentWidth} m`", scan_area_js)
        self.assertIn("function updateMarkerDetailMode()", app_js)
        self.assertIn("map.on('zoomend', updateMarkerDetailMode)", app_js)
        self.assertIn("function setStep(id, state, label = null, meta = null)", app_js)
        self.assertIn("function setStep(id, state, label = null, meta = null)", scan_progress_js)
        self.assertNotIn("function setStep(id, state, label = null, meta = null)", app_main_js)
        self.assertIn("function startDownloadProgressPolling()", scan_progress_js)
        self.assertNotIn("function startDownloadProgressPolling()", app_main_js)
        self.assertIn("function resetProgress()", scan_progress_js)
        self.assertNotIn("function resetProgress()", app_main_js)
        self.assertIn("map.on('popupopen'", app_js)
        self.assertIn("crosshair?.classList.toggle(", app_js)
        self.assertIn("'is-hidden',", app_js)
        self.assertIn("let crosshairVisibilityControllerReady = false", app_js)
        self.assertIn("crosshairVisibilityControllerReady = true;\nupdateCrosshairVisibility();", app_js)
        self.assertIn(
            "let crosshairManuallyHidden = localStorage.getItem(CROSSHAIR_HIDDEN_STORAGE_KEY) === '1'", app_js
        )
        self.assertIn("function toggleCrosshairFromContextMenu()", app_js)
        self.assertIn("if (!publicFeatureAllowed(PUBLIC_FEATURE_KEYS.scanAnalysis)) return;", app_js)
        self.assertIn("function setCrosshairManuallyHidden(hidden)", app_js)
        self.assertIn("localStorage.setItem(CROSSHAIR_HIDDEN_STORAGE_KEY", app_js)
        self.assertIn("function updateContextCrosshairLabel()", app_js)
        self.assertIn("document.addEventListener('langchange', updateContextCrosshairLabel)", app_js)
        self.assertIn('id="map-context-menu"', html)
        self.assertIn('id="context-toggle-crosshair"', html)
        self.assertIn('id="context-center-scan" onclick="centerScanOnContextPoint()" hidden', html)
        self.assertIn(
            'id="context-identify-parcel" onclick="identifyCadastralParcelAtContextPoint()" hidden',
            html,
        )
        self.assertIn('id="context-add-field-photos" onclick="openFieldPhotoUploadAtContextPoint()" hidden', html)
        self.assertIn('id="context-toggle-crosshair" onclick="toggleCrosshairFromContextMenu()" hidden', html)
        self.assertIn('id="context-crosshair-label"', html)
        self.assertIn('onclick="toggleCrosshairFromContextMenu()"', html)
        self.assertIn("map.on('contextmenu'", app_js)
        self.assertIn("function centerScanOnContextPoint()", app_js)
        self.assertIn('id="context-center-scan"', html)
        self.assertIn(
            "if (!publicFeatureAllowed(PUBLIC_FEATURE_KEYS.scanAnalysis) || !contextMenuLatLng) return;", app_js
        )
        self.assertIn("function openFieldPhotoUploadAtContextPoint()", app_js)
        self.assertIn('onclick="openFieldPhotoUploadAtContextPoint()"', html)
        self.assertIn("function identifyCadastralParcelAtContextPoint()", app_js)
        self.assertIn('id="context-identify-parcel"', html)
        self.assertIn("if (!publicLayerAllowed(PUBLIC_LAYER_KEYS.cadastral) || !contextMenuLatLng) return;", app_js)
        self.assertIn("function cadastralParcelPopup(parcel = {})", app_js)
        self.assertIn("function cadastralCodeLabel(code)", app_js)
        self.assertIn("function cadastralParcelGeoportalUrl(parcel = {})", app_js)
        self.assertIn("function copyActiveCadastralParcel()", app_js)
        self.assertIn("const CADASTRAL_LAND_USE_LABEL_KEYS", app_js)
        self.assertIn("parcel.land_use || parcel.contour", app_js)
        self.assertIn("const contourLabel = cadastralCodeLabel(parcel.contour)", app_js)
        self.assertIn("contourLabel !== terrainType && contourLabel !== landUse", app_js)
        self.assertIn("const data = await apiJson(url, { cache: 'no-store' })", app_js)
        self.assertIn("const CADASTRAL_IDENTIFY_URL = '/api/cadastral/identify'", config_js)
        self.assertIn("let fieldPhotoUploadFallbackLatLng = null", app_js)
        self.assertIn("function currentFieldPhotoUploadFallbackLatLng()", app_js)
        self.assertIn("function fieldPhotoAnyIssueAllowed()", app_js)
        self.assertIn("function copyContextCoords()", app_js)
        self.assertIn("function copyContextPlaceLink()", app_js)
        self.assertIn("appPlaceUrl(contextMenuLatLng.lat, contextMenuLatLng.lng, map.getZoom())", app_js)
        self.assertIn("'context.centerScan': 'Ustaw środek skanu'", i18n_js)
        self.assertIn("'context.addFieldPhotos': 'Dodaj zdjęcia tutaj'", i18n_js)
        self.assertIn("'context.identifyParcel': 'Sprawdź działkę'", i18n_js)
        self.assertIn("'context.parcelTerrainType': 'Typ terenu'", i18n_js)
        self.assertIn("'context.parcelLandUse': 'Użytek'", i18n_js)
        self.assertIn("'context.parcelContour': 'Kontur'", i18n_js)
        self.assertIn("'context.parcelCopyData': 'Kopiuj dane działki'", i18n_js)
        self.assertIn("'context.landUse.dr': 'droga / pas drogowy'", i18n_js)
        self.assertNotIn("context.parcelOwnerHint", i18n_js)
        self.assertNotIn("context.parcelSurfaceHint", i18n_js)
        self.assertNotIn("context.parcelRegistryGroupMissing", i18n_js)
        self.assertNotIn("parcel.registry_group || t('context.parcelRegistryGroupMissing')", app_js)
        self.assertIn("'context.hideCrosshair': 'Ukryj celownik'", i18n_js)
        self.assertIn("'context.showCrosshair': 'Pokaż celownik'", i18n_js)
        self.assertIn("'context.copyPlaceLink': 'Skopiuj link do miejsca'", i18n_js)
        self.assertIn("'context.copiedPlaceLink': 'Skopiowano link do miejsca.'", i18n_js)
        self.assertIn('data-i18n="context.addFieldPhotos"', html)
        self.assertIn('data-i18n="context.identifyParcel"', html)
        self.assertIn('data-i18n="context.hideCrosshair"', html)
        self.assertIn('data-i18n="context.copyPlaceLink"', html)
        self.assertIn('class="modal modal--welcome draggable-modal"', html)
        self.assertNotIn('id="welcome-add-photo"', html)
        self.assertNotIn('onclick="centerMapOnBrowserLocation()"', html)
        self.assertNotIn('onclick="openFieldPhotoUploadAtMapCenter()"', html)
        self.assertNotIn("function centerMapOnBrowserLocation()", app_js)
        self.assertNotIn("navigator.geolocation", app_js)
        self.assertIn("function openWelcomeModalIfNeeded()", app_js)
        self.assertIn("function openWelcomeModalFromAdminPanel()", app_js)
        self.assertIn("localStorage.removeItem(WELCOME_MODAL_SEEN_STORAGE_KEY)", app_js)
        self.assertIn("closeModal(document.getElementById('modal-admin-panel'))", app_js)
        self.assertIn("WELCOME_MODAL_SEEN_STORAGE_KEY", app_js)
        self.assertNotIn("function openFieldPhotoUploadAtMapCenter()", app_js)
        self.assertNotIn(".welcome-secondary-btn", styles)
        self.assertIn(
            "'modal.help.dataSource': 'Data: OSM, Polish Geoportal, and Wrocław orthophotos for YOLO analysis.'",
            i18n_js,
        )
        self.assertIn(".modal--welcome", styles)
        self.assertIn(".welcome-actions", styles)
        self.assertIn("#crosshair.is-hidden", styles)
        self.assertIn(".map-context-menu", styles)
        self.assertIn(".marker-detail--compact .map-pin-count", styles)
        self.assertIn(".marker-detail--dots .saved-wreck-pin", styles)
        self.assertIn(".marker-detail--dots .field-photo-pin", styles)
        self.assertIn(".parcel-popup-row", styles)


if __name__ == "__main__":
    unittest.main()
