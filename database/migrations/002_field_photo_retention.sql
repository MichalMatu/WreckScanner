ALTER TABLE field_photos ADD COLUMN private_original_replaced_at TEXT;
ALTER TABLE field_photos ADD COLUMN private_original_deleted_at TEXT;
ALTER TABLE field_photos ADD COLUMN private_original_retention_action TEXT;

INSERT OR IGNORE INTO schema_migrations (version)
VALUES ('002_field_photo_retention');
