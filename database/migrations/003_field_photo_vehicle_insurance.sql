ALTER TABLE field_photos ADD COLUMN vehicle_insurance_status TEXT NOT NULL DEFAULT 'unknown'
    CHECK (vehicle_insurance_status IN ('unknown', 'insured', 'uninsured'));

INSERT OR IGNORE INTO schema_migrations (version)
VALUES ('003_field_photo_vehicle_insurance');
