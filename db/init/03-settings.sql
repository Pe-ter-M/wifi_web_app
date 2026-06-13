-- Settings table and seed data for Phantom Internet Providers
-- This runs after 01-freeradius-schema.sql and 02-billing-schema.sql

CREATE TABLE IF NOT EXISTS settings (
    key         text PRIMARY KEY,
    value       text NOT NULL,
    updated_at  timestamp with time zone NOT NULL DEFAULT now()
);

-- Seed default company settings and default plans if empty

INSERT INTO settings (key, value) VALUES
    ('company', '{"name":"Phantom Internet Providers","short_name":"PhantomNet","tagline":"Connect with confidence","currency":"KSH","currency_symbol":"KSh","support_email":"support@phantomnet.co.ke","support_phone":"+254 700 000000"}'),
    ('defaults', '{"max_devices":1,"session_timeout":86400,"idle_timeout":600}')
ON CONFLICT (key) DO NOTHING;
