PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;

BEGIN;

CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
) STRICT;

CREATE TABLE IF NOT EXISTS field_photos (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    captured_at TEXT,
    issue_type TEXT NOT NULL CHECK (issue_type IN ('vehicle', 'infrastructure', 'smoke')),
    lat REAL NOT NULL CHECK (lat >= -90.0 AND lat <= 90.0),
    lon REAL NOT NULL CHECK (lon >= -180.0 AND lon <= 180.0),
    coordinate_source TEXT NOT NULL,
    position_updated_at TEXT,
    public_review_status TEXT NOT NULL CHECK (public_review_status IN ('draft', 'pending', 'approved', 'rejected')),
    reviewed_at TEXT,
    redactions_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(redactions_json)),
    original_filename TEXT NOT NULL,
    content_type TEXT NOT NULL,
    format TEXT NOT NULL,
    size_bytes INTEGER NOT NULL CHECK (size_bytes >= 0),
    image_width INTEGER CHECK (image_width IS NULL OR image_width > 0),
    image_height INTEGER CHECK (image_height IS NULL OR image_height > 0),
    private_original_file TEXT NOT NULL,
    public_image_file TEXT,
    public_thumb_file TEXT,
    public_width INTEGER CHECK (public_width IS NULL OR public_width > 0),
    public_height INTEGER CHECK (public_height IS NULL OR public_height > 0),
    submission_owner TEXT,
    edit_token_salt TEXT,
    edit_token_hash TEXT,
    edit_token_created_at TEXT,
    links_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(links_json)),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
) STRICT;

CREATE INDEX IF NOT EXISTS idx_field_photos_issue_review
    ON field_photos (issue_type, public_review_status);

CREATE INDEX IF NOT EXISTS idx_field_photos_location
    ON field_photos (lat, lon);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value_json TEXT NOT NULL CHECK (json_valid(value_json)),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
) STRICT;

CREATE TABLE IF NOT EXISTS privacy_requests (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('new', 'in_progress', 'done', 'rejected')),
    email TEXT NOT NULL,
    target TEXT NOT NULL,
    reason TEXT NOT NULL,
    handled_at TEXT,
    admin_note TEXT NOT NULL DEFAULT ''
) STRICT;

CREATE INDEX IF NOT EXISTS idx_privacy_requests_status_updated
    ON privacy_requests (status, updated_at);

INSERT OR IGNORE INTO schema_migrations (version)
VALUES ('001_initial');

COMMIT;
