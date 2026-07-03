from dataclasses import dataclass
from pathlib import Path

BYTES_PER_MIB = 1024 * 1024
BYTES_PER_GIB = 1024 * BYTES_PER_MIB

DIAGNOSTICS_DIR = Path("analiza")
WRECKS_DIR = Path("zidentyfikowane_wraki")
FIELD_PHOTOS_DIR = Path("zdjecia_terenowe")
PRIVATE_PHOTOS_DIR = Path("prywatne_zdjecia")
PRIVACY_REQUESTS_DIR = Path("zgloszenia_prywatnosci")

ORTHO_WMS_BASE = "https://gis1.um.wroc.pl/arcgis/services/ogc"
ORTHO_YEARS = [2020, 2021, 2022, 2023, 2024, 2025]
ORTHO_CROP_PIXELS_PER_METER = 20.0
ORTHO_CROP_MIN_PX = 180
ORTHO_CROP_MAX_PX = 800
ORTHO_WMS_TIMEOUT = (2, 5)
ORTHO_CROP_MAX_WORKERS = 4
ORTHO_BLANK_IMAGE_STD_THRESHOLD = 10.0


@dataclass(frozen=True)
class EnhancementSettings:
    """Konfiguracja filtra ortofoto używanego w podglądzie mapy."""

    enabled: bool = True
    clahe_clip_limit: float = 1.5
    clahe_tile_grid_size: int = 8
    l_percentile_low: float = 2.0
    l_percentile_high: float = 98.0
    l_output_low: float = 10.0
    l_output_high: float = 245.0
    l_min_percentile_span: float = 5.0
    decast_strength: float = 0.4


DEFAULT_ENHANCEMENT_SETTINGS = EnhancementSettings()
REVIEW_CROP_M = 7.5
REVIEW_CROP_M_MIN = 5.0
REVIEW_CROP_M_MAX = 20.0
REVIEW_JPEG_QUALITY = 95
WRECK_DEDUPE_M = 3.0

# Uploady i raporty. Zwiększenie limitów poprawia wygodę, ale podnosi zużycie
# pamięci przy parsowaniu multipart i rozmiar lokalnych paczek zgłoszeniowych.
ALLOWED_UPLOAD_IMAGE_FORMATS = {
    "JPEG": (".jpg", "image/jpeg"),
    "PNG": (".png", "image/png"),
    "WEBP": (".webp", "image/webp"),
}
MAX_FIELD_PHOTO_BYTES = 10 * BYTES_PER_MIB
FIELD_PHOTO_MAX_BODY_BYTES = 12 * BYTES_PER_MIB
FIELD_PHOTO_THUMBNAIL_MAX_EDGE_PX = 360
FIELD_PHOTO_THUMBNAIL_JPEG_QUALITY = 82
PUBLIC_PHOTO_JPEG_QUALITY = 88
PRIVATE_ORIGINAL_RETENTION_DAYS = 180
DEFAULT_FIELD_PHOTO_ISSUE_TYPE = "vehicle"
# Typ obserwacji zapisany przy zdjęciu terenowym. Dodanie nowego typu tutaj
# pozwala rozróżniać pinezki bez mieszania ich z logiką teczek pojazdów.
FIELD_PHOTO_ISSUE_TYPES = {
    "vehicle": "zdjęcie pojazdu",
    "infrastructure": "niebezpieczna infrastruktura",
    "smoke": "dym papierosowy",
}

MAX_WRECK_PHOTO_BYTES = 10 * BYTES_PER_MIB
MAX_WRECK_PHOTOS_PER_UPLOAD = 25
MAX_WRECK_PHOTO_BODY_BYTES = (MAX_WRECK_PHOTOS_PER_UPLOAD * MAX_WRECK_PHOTO_BYTES) + (2 * BYTES_PER_MIB)
WRECK_PHOTO_THUMB_MAX_EDGE_PX = 900
WRECK_PHOTO_THUMB_QUALITY = 84

REPORT_RECIPIENT = "interwencje@smwroclaw.pl"
MAX_REPORT_PACKAGE_BODY_BYTES = 2 * BYTES_PER_MIB

# Publiczne dodawanie spraw/zdjęć zapisuje materiały jako "pending".
# Limity chronią dysk przed zalaniem kolejki przed moderacją.
PENDING_SUBMISSION_MAX_BYTES = 512 * BYTES_PER_MIB
PENDING_SUBMISSION_MAX_ITEMS = 100

# Ustawienia trwałe widoczne w panelu.
SETTINGS_FILENAME = "settings.json"
