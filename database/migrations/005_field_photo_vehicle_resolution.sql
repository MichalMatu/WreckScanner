ALTER TABLE field_photos ADD COLUMN vehicle_resolution_status TEXT NOT NULL DEFAULT 'active'
    CHECK (vehicle_resolution_status IN ('active', 'removed'));
ALTER TABLE field_photos ADD COLUMN vehicle_resolution_updated_at TEXT;

CREATE INDEX IF NOT EXISTS idx_field_photos_vehicle_resolution
    ON field_photos (issue_type, vehicle_resolution_status, public_review_status);

INSERT OR IGNORE INTO schema_migrations (version)
VALUES ('005_field_photo_vehicle_resolution');
