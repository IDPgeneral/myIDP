BEGIN;

INSERT INTO products (name, slug, description, status, owner)
VALUES
    ('MILU Software', 'milu-software', 'Produto MILU Software', 'unknown', 'REPLACE_ME'),
    ('ColorGlass', 'colorglass', 'Produto ColorGlass', 'unknown', 'REPLACE_ME'),
    ('Super Excel', 'super-excel', 'Produto Super Excel', 'unknown', 'REPLACE_ME')
ON CONFLICT (slug) DO NOTHING;

INSERT INTO product_environments (product_id, name, required)
SELECT id, 'production', true FROM products
WHERE slug IN ('milu-software', 'colorglass', 'super-excel')
ON CONFLICT (product_id, name) DO NOTHING;

INSERT INTO provider_accounts (provider, name, product_id, credential_ref, status, connection_status)
SELECT 'github', 'github-milu', id, 'GITHUB_INSTALLATION_ID_MILU', 'not_configured', 'not_configured'
FROM products WHERE slug = 'milu-software'
ON CONFLICT (name) DO NOTHING;
INSERT INTO provider_accounts (provider, name, product_id, credential_ref, status, connection_status)
SELECT 'render', 'render-milu', id, 'RENDER_API_KEY_MILU', 'not_configured', 'not_configured'
FROM products WHERE slug = 'milu-software'
ON CONFLICT (name) DO NOTHING;
INSERT INTO provider_accounts (provider, name, product_id, credential_ref, status, connection_status)
SELECT 'supabase', 'supabase-milu', id, 'SUPABASE_MANAGEMENT_TOKEN_MILU', 'not_configured', 'not_configured'
FROM products WHERE slug = 'milu-software'
ON CONFLICT (name) DO NOTHING;

INSERT INTO provider_accounts (provider, name, product_id, credential_ref, status, connection_status)
SELECT 'github', 'github-colorglass', id, 'GITHUB_INSTALLATION_ID_COLORGLASS', 'not_configured', 'not_configured'
FROM products WHERE slug = 'colorglass'
ON CONFLICT (name) DO NOTHING;
INSERT INTO provider_accounts (provider, name, product_id, credential_ref, status, connection_status)
SELECT 'render', 'render-colorglass', id, 'RENDER_API_KEY_COLORGLASS', 'not_configured', 'not_configured'
FROM products WHERE slug = 'colorglass'
ON CONFLICT (name) DO NOTHING;
INSERT INTO provider_accounts (provider, name, product_id, credential_ref, status, connection_status)
SELECT 'supabase', 'supabase-colorglass', id, 'SUPABASE_MANAGEMENT_TOKEN_COLORGLASS', 'not_configured', 'not_configured'
FROM products WHERE slug = 'colorglass'
ON CONFLICT (name) DO NOTHING;

INSERT INTO provider_accounts (provider, name, product_id, credential_ref, status, connection_status)
SELECT 'github', 'github-superexcel', id, 'GITHUB_INSTALLATION_ID_SUPEREXCEL', 'not_configured', 'not_configured'
FROM products WHERE slug = 'super-excel'
ON CONFLICT (name) DO NOTHING;
INSERT INTO provider_accounts (provider, name, product_id, credential_ref, status, connection_status)
SELECT 'render', 'render-superexcel', id, 'RENDER_API_KEY_SUPEREXCEL', 'not_configured', 'not_configured'
FROM products WHERE slug = 'super-excel'
ON CONFLICT (name) DO NOTHING;
INSERT INTO provider_accounts (provider, name, product_id, credential_ref, status, connection_status)
SELECT 'supabase', 'supabase-superexcel', id, 'SUPABASE_MANAGEMENT_TOKEN_SUPEREXCEL', 'not_configured', 'not_configured'
FROM products WHERE slug = 'super-excel'
ON CONFLICT (name) DO NOTHING;

COMMIT;
