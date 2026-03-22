-- =============================================================================
-- Blacklistify Table Setup
-- Run this in Supabase SQL Editor: https://supabase.com/dashboard/project/kjkjlkerljmukyzfqfji/sql
-- All tables in public schema with blf_ prefix
-- =============================================================================

-- Users (local blacklistify users)
CREATE TABLE IF NOT EXISTS blf_users (
    id              BIGSERIAL PRIMARY KEY,
    username        TEXT NOT NULL UNIQUE,
    email           TEXT NOT NULL UNIQUE,
    phone_number    TEXT NOT NULL DEFAULT '',
    hashed_password TEXT NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    is_staff        BOOLEAN NOT NULL DEFAULT FALSE,
    is_superuser    BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Legacy hostname monitors
CREATE TABLE IF NOT EXISTS blf_hostnames (
    id                  BIGSERIAL PRIMARY KEY,
    user_id             BIGINT NOT NULL REFERENCES blf_users(id) ON DELETE CASCADE,
    hostname_type       TEXT NOT NULL DEFAULT 'domain',
    hostname            TEXT NOT NULL,
    description         TEXT,
    is_alert_enabled    BOOLEAN NOT NULL DEFAULT FALSE,
    is_monitor_enabled  BOOLEAN NOT NULL DEFAULT FALSE,
    status              TEXT NOT NULL DEFAULT 'active',
    is_blacklisted      BOOLEAN NOT NULL DEFAULT FALSE,
    created             TIMESTAMPTZ DEFAULT NOW(),
    updated             TIMESTAMPTZ DEFAULT NOW()
);

-- Legacy check history
CREATE TABLE IF NOT EXISTS blf_check_histories (
    id              BIGSERIAL PRIMARY KEY,
    hostname_id     BIGINT NOT NULL REFERENCES blf_hostnames(id) ON DELETE CASCADE,
    result          JSONB,
    status          TEXT NOT NULL DEFAULT 'current',
    created         TIMESTAMPTZ DEFAULT NOW(),
    updated         TIMESTAMPTZ DEFAULT NOW()
);

-- Scan jobs
CREATE TABLE IF NOT EXISTS blf_scan_jobs (
    id              BIGSERIAL PRIMARY KEY,
    job_type        TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending',
    total_subnets   INT DEFAULT 0,
    total_ips       INT DEFAULT 0,
    scanned_ips     INT DEFAULT 0,
    blacklisted_ips INT DEFAULT 0,
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    error_message   TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Scan results (per IP)
CREATE TABLE IF NOT EXISTS blf_scan_results (
    id                  BIGSERIAL PRIMARY KEY,
    scan_job_id         BIGINT NOT NULL REFERENCES blf_scan_jobs(id) ON DELETE CASCADE,
    block_id            UUID,
    block_cidr          TEXT NOT NULL,
    prefix_id           UUID,
    prefix_cidr         TEXT,
    ip_address          INET NOT NULL,
    is_blacklisted      BOOLEAN DEFAULT FALSE,
    providers_detected  JSONB DEFAULT '[]',
    providers_total     INT DEFAULT 0,
    checked_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_blf_sr_block_id ON blf_scan_results(block_id);
CREATE INDEX IF NOT EXISTS idx_blf_sr_block_cidr ON blf_scan_results(block_cidr);
CREATE INDEX IF NOT EXISTS idx_blf_sr_ip ON blf_scan_results(ip_address);
CREATE INDEX IF NOT EXISTS idx_blf_sr_blacklisted ON blf_scan_results(is_blacklisted) WHERE is_blacklisted = TRUE;
CREATE INDEX IF NOT EXISTS idx_blf_sr_job ON blf_scan_results(scan_job_id);
CREATE INDEX IF NOT EXISTS idx_blf_sr_checked ON blf_scan_results(checked_at DESC);

-- Block status (aggregate cache per /24)
CREATE TABLE IF NOT EXISTS blf_block_status (
    block_id            UUID PRIMARY KEY,
    block_cidr          TEXT NOT NULL,
    prefix_id           UUID,
    prefix_cidr         TEXT,
    customer_name       TEXT,
    total_ips           INT DEFAULT 0,
    blacklisted_ips     INT DEFAULT 0,
    clean_ips           INT DEFAULT 0,
    blacklist_rate      NUMERIC(5,4) DEFAULT 0,
    worst_providers     JSONB DEFAULT '[]',
    last_scan_job_id    BIGINT,
    last_scanned_at     TIMESTAMPTZ,
    status_changed_at   TIMESTAMPTZ,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_blf_bs_prefix ON blf_block_status(prefix_id);

-- API keys
CREATE TABLE IF NOT EXISTS blf_api_keys (
    id              BIGSERIAL PRIMARY KEY,
    key_prefix      TEXT NOT NULL,
    key_hash        TEXT NOT NULL,
    name            TEXT NOT NULL,
    scopes          JSONB DEFAULT '["read"]',
    is_active       BOOLEAN DEFAULT TRUE,
    last_used_at    TIMESTAMPTZ,
    expires_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_blf_ak_prefix ON blf_api_keys(key_prefix);

-- Webhooks
CREATE TABLE IF NOT EXISTS blf_webhooks (
    id                  BIGSERIAL PRIMARY KEY,
    url                 TEXT NOT NULL,
    events              JSONB NOT NULL,
    secret              TEXT NOT NULL,
    is_active           BOOLEAN DEFAULT TRUE,
    last_triggered_at   TIMESTAMPTZ,
    failure_count       INT DEFAULT 0,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- Alert rules
CREATE TABLE IF NOT EXISTS blf_alert_rules (
    id              BIGSERIAL PRIMARY KEY,
    name            TEXT NOT NULL,
    condition_type  TEXT NOT NULL,
    threshold       NUMERIC,
    subnet_filter   TEXT,
    webhook_id      BIGINT REFERENCES blf_webhooks(id) ON DELETE SET NULL,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS but allow service_role full access
ALTER TABLE blf_users ENABLE ROW LEVEL SECURITY;
ALTER TABLE blf_hostnames ENABLE ROW LEVEL SECURITY;
ALTER TABLE blf_check_histories ENABLE ROW LEVEL SECURITY;
ALTER TABLE blf_scan_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE blf_scan_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE blf_block_status ENABLE ROW LEVEL SECURITY;
ALTER TABLE blf_api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE blf_webhooks ENABLE ROW LEVEL SECURITY;
ALTER TABLE blf_alert_rules ENABLE ROW LEVEL SECURITY;

-- Service role bypass policies (our backend uses service_role key)
CREATE POLICY "service_role_all" ON blf_users FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all" ON blf_hostnames FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all" ON blf_check_histories FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all" ON blf_scan_jobs FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all" ON blf_scan_results FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all" ON blf_block_status FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all" ON blf_api_keys FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all" ON blf_webhooks FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all" ON blf_alert_rules FOR ALL USING (true) WITH CHECK (true);
