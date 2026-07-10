from dataclasses import dataclass
from pathlib import Path

BYTES_PER_MIB = 1024 * 1024
BYTES_PER_GIB = 1024 * BYTES_PER_MIB

DIAGNOSTICS_DIR = Path("analiza")
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
ORTHO_CROP_RETRY_ATTEMPTS = 3
ORTHO_CROP_RETRY_DELAY_SECONDS = 0.35
ORTHO_BLANK_IMAGE_STD_THRESHOLD = 0.5


@dataclass(frozen=True)
class EnhancementSettings:
    """Konfiguracja filtra ortofoto używanego w podglądzie mapy."""

    enabled: bool = False
    clahe_clip_limit: float = 0.8
    clahe_tile_grid_size: int = 12
    l_percentile_low: float = 1.0
    l_percentile_high: float = 99.0
    l_output_low: float = 5.0
    l_output_high: float = 250.0
    l_min_percentile_span: float = 5.0
    decast_strength: float = 0.2


DEFAULT_ENHANCEMENT_SETTINGS = EnhancementSettings()
REVIEW_CROP_M = 7.5
REVIEW_CROP_M_MIN = 5.0
REVIEW_CROP_M_MAX = 20.0
REVIEW_JPEG_QUALITY = 95

# Uploady i raporty. Zwiększenie limitów poprawia wygodę, ale podnosi zużycie
# pamięci przy parsowaniu multipart i generowaniu PDF.
ALLOWED_UPLOAD_IMAGE_FORMATS = {
    "JPEG": (".jpg", "image/jpeg"),
    "PNG": (".png", "image/png"),
    "WEBP": (".webp", "image/webp"),
}
MAX_FIELD_PHOTO_BYTES = 10 * BYTES_PER_MIB
FIELD_PHOTO_MAX_BODY_BYTES = 12 * BYTES_PER_MIB
MAX_FIELD_PHOTO_PIXELS = 50_000_000
MAX_FIELD_PHOTO_EDGE_PX = 12_000
FIELD_PHOTO_MAX_CONCURRENT_DECODES = 2
MAX_PHOTO_REDACTIONS = 100
MAX_REDACTION_POINTS = 64
FIELD_PHOTO_THUMBNAIL_MAX_EDGE_PX = 360
FIELD_PHOTO_THUMBNAIL_JPEG_QUALITY = 82
PUBLIC_PHOTO_JPEG_QUALITY = 88
PRIVATE_ORIGINAL_RETENTION_DAYS = 180
PRIVACY_REQUEST_CONTENT_RETENTION_DAYS = 90
DEFAULT_FIELD_PHOTO_ISSUE_TYPE = "vehicle"
FIELD_PHOTO_ISSUE_TYPES = {
    "vehicle": "zdjęcie pojazdu",
    "infrastructure": "niebezpieczna infrastruktura",
    "smoke": "dym papierosowy",
}
DEFAULT_FIELD_PHOTO_VEHICLE_INSURANCE_STATUS = "unknown"
FIELD_PHOTO_VEHICLE_INSURANCE_STATUSES = {
    "unknown": "nie sprawdzono OC",
    "insured": "pojazd ma OC",
    "uninsured": "brak OC",
}
DEFAULT_FIELD_PHOTO_VEHICLE_RESOLUTION_STATUS = "active"
FIELD_PHOTO_VEHICLE_RESOLUTION_STATUSES = {
    "active": "pojazd aktywny",
    "removed": "pojazd usunięty",
}
FIELD_PHOTO_GROUP_RADIUS_M = 1.0

REPORT_RECIPIENT = "interwencje@smwroclaw.pl"
MAX_REPORT_PDF_BODY_BYTES = 2 * BYTES_PER_MIB
MAX_REPORT_PHOTOS = 25
MAX_REPORT_PUBLIC_PHOTO_BYTES = 80 * BYTES_PER_MIB
MAX_OWNER_PHOTO_IDS = 25
MAX_ORTHO_RESPONSE_BYTES = 12 * BYTES_PER_MIB

# Publiczne dodawanie zdjęć zapisuje materiały jako "pending".
# Limity chronią dysk przed zalaniem kolejki przed moderacją.
PENDING_SUBMISSION_MAX_BYTES = 512 * BYTES_PER_MIB
PENDING_SUBMISSION_MAX_ITEMS = 100

# Ustawienia trwałe widoczne w panelu.
SETTINGS_FILENAME = "settings.json"
DATABASE_PATH = Path("wreckscanner.sqlite3")
DATABASE_MIGRATIONS_DIR = Path("database/migrations")
