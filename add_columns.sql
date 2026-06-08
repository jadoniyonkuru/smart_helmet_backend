-- Run once against smart_helmet_db to apply all schema additions.
-- psql -U postgres -d smart_helmet_db -f add_columns.sql

-- New columns on existing tables
ALTER TABLE sensor_data
    ADD COLUMN IF NOT EXISTS battery_level   FLOAT,
    ADD COLUMN IF NOT EXISTS signal_strength INTEGER;

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS avatar_url VARCHAR(500);

-- New tables
CREATE TABLE IF NOT EXISTS notifications (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title             VARCHAR(255) NOT NULL,
    message           TEXT NOT NULL,
    type              VARCHAR(20) NOT NULL DEFAULT 'info',
    is_read           BOOLEAN NOT NULL DEFAULT FALSE,
    related_helmet_id UUID REFERENCES helmets(id) ON DELETE SET NULL,
    related_alert_id  UUID REFERENCES alerts(id)  ON DELETE SET NULL,
    created_at        TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS system_health_logs (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cpu_percent    FLOAT NOT NULL,
    memory_percent FLOAT NOT NULL,
    disk_percent   FLOAT NOT NULL,
    recorded_at    TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Index for fast per-user notification lookups
CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_system_health_recorded_at ON system_health_logs(recorded_at);
