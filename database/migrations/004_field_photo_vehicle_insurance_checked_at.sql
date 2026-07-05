ALTER TABLE field_photos ADD COLUMN vehicle_insurance_checked_at TEXT;

INSERT OR IGNORE INTO schema_migrations (version)
VALUES ('004_field_photo_vehicle_insurance_checked_at');
