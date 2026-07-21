BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS users (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    email text NOT NULL UNIQUE,
    display_name text,
    role text NOT NULL DEFAULT 'viewer' CHECK (role IN ('viewer', 'admin')),
    active boolean NOT NULL DEFAULT true,
    last_login_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS products (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL,
    slug text NOT NULL UNIQUE,
    description text,
    status text NOT NULL DEFAULT 'unknown',
    owner text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS product_environments (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id uuid NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    name text NOT NULL CHECK (name IN ('production', 'staging', 'development')),
    required boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (product_id, name)
);

CREATE TABLE IF NOT EXISTS provider_accounts (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    provider text NOT NULL CHECK (provider IN ('github', 'render', 'supabase')),
    name text NOT NULL UNIQUE,
    product_id uuid NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    credential_ref text NOT NULL,
    external_account_id text,
    status text NOT NULL DEFAULT 'not_configured',
    connection_status text NOT NULL DEFAULT 'not_configured',
    last_sync_at timestamptz,
    last_validated_at timestamptz,
    last_error text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CHECK (credential_ref ~ '^[A-Z][A-Z0-9_]{2,127}$')
);

CREATE TABLE IF NOT EXISTS product_resources (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id uuid NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    provider_account_id uuid REFERENCES provider_accounts(id) ON DELETE RESTRICT,
    resource_type text NOT NULL CHECK (resource_type IN ('repository', 'render_service', 'supabase_project', 'health_endpoint', 'documentation', 'domain')),
    external_id text NOT NULL,
    name text NOT NULL,
    environment text NOT NULL DEFAULT 'production' CHECK (environment IN ('production', 'staging', 'development')),
    url text,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (provider_account_id, resource_type, external_id)
);

CREATE TABLE IF NOT EXISTS health_checks (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id uuid NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    resource_id uuid REFERENCES product_resources(id) ON DELETE SET NULL,
    name text NOT NULL,
    url text NOT NULL,
    method text NOT NULL DEFAULT 'GET',
    expected_status integer NOT NULL DEFAULT 200,
    timeout_seconds integer NOT NULL DEFAULT 8 CHECK (timeout_seconds BETWEEN 1 AND 60),
    active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS health_check_results (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    health_check_id uuid NOT NULL REFERENCES health_checks(id) ON DELETE CASCADE,
    status text NOT NULL CHECK (status IN ('healthy', 'degraded', 'down', 'unknown')),
    http_status integer,
    response_time_ms integer,
    message text NOT NULL,
    checked_at timestamptz NOT NULL DEFAULT now(),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS sync_runs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    target_type text NOT NULL,
    target_id text,
    product_id uuid REFERENCES products(id) ON DELETE SET NULL,
    provider_account_id uuid REFERENCES provider_accounts(id) ON DELETE SET NULL,
    resource_id uuid REFERENCES product_resources(id) ON DELETE SET NULL,
    provider text,
    status text NOT NULL DEFAULT 'running',
    started_at timestamptz NOT NULL DEFAULT now(),
    finished_at timestamptz,
    error text,
    correlation_id text,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS resource_snapshots (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    provider text NOT NULL,
    snapshot_type text NOT NULL,
    resource_id uuid NOT NULL REFERENCES product_resources(id) ON DELETE CASCADE,
    captured_at timestamptz NOT NULL DEFAULT now(),
    status text NOT NULL,
    summary jsonb NOT NULL DEFAULT '{}'::jsonb,
    payload_sanitized jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid REFERENCES users(id) ON DELETE SET NULL,
    product_id uuid REFERENCES products(id) ON DELETE SET NULL,
    provider_account_id uuid REFERENCES provider_accounts(id) ON DELETE SET NULL,
    resource_id uuid REFERENCES product_resources(id) ON DELETE SET NULL,
    action text NOT NULL,
    before_data jsonb,
    after_data jsonb,
    success boolean NOT NULL,
    error text,
    correlation_id text,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_products_slug ON products(slug);
CREATE INDEX IF NOT EXISTS ix_provider_accounts_product_id ON provider_accounts(product_id);
CREATE INDEX IF NOT EXISTS ix_provider_accounts_provider ON provider_accounts(provider);
CREATE INDEX IF NOT EXISTS ix_provider_accounts_product_provider ON provider_accounts(product_id, provider);
CREATE INDEX IF NOT EXISTS ix_product_resources_product_id ON product_resources(product_id);
CREATE INDEX IF NOT EXISTS ix_product_resources_provider_account_id ON product_resources(provider_account_id);
CREATE INDEX IF NOT EXISTS ix_product_resources_external_id ON product_resources(external_id);
CREATE INDEX IF NOT EXISTS ix_sync_runs_created_at ON sync_runs(created_at DESC);
CREATE INDEX IF NOT EXISTS ix_health_check_results_check_created ON health_check_results(health_check_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_resource_snapshots_resource_captured ON resource_snapshots(resource_id, captured_at DESC);
CREATE INDEX IF NOT EXISTS ix_audit_logs_created_at ON audit_logs(created_at DESC);

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE products ENABLE ROW LEVEL SECURITY;
ALTER TABLE product_environments ENABLE ROW LEVEL SECURITY;
ALTER TABLE provider_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE product_resources ENABLE ROW LEVEL SECURITY;
ALTER TABLE health_checks ENABLE ROW LEVEL SECURITY;
ALTER TABLE health_check_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE sync_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE resource_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

COMMIT;
