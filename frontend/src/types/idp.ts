export type StatusName =
  | "healthy"
  | "degraded"
  | "down"
  | "unknown"
  | "syncing"
  | "error"
  | "authentication_error"
  | "permission_error"
  | "provider_unavailable"
  | "not_configured"
  | "connected";

export interface HealthResult {
  health_check_id: string;
  name: string;
  status: string;
  http_status: number | null;
  response_time_ms: number | null;
  message: string;
  checked_at: string | null;
}

export interface ProductSummary {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  owner: string;
  status: string;
  github_status: string;
  render_status: string;
  supabase_status: string;
  last_commit: Record<string, unknown> | null;
  last_deploy: Record<string, unknown> | null;
  ci: Record<string, unknown> | null;
  health: HealthResult | null;
  last_sync_at: string | null;
  alert_count: number;
}

export interface ProviderAccount {
  id: string;
  provider: string;
  name: string;
  product_id: string;
  credential_ref: string;
  external_account_id: string | null;
  status: string;
  connection_status: string;
  credential_configured: boolean;
  last_sync_at: string | null;
  last_validated_at: string | null;
  last_error: string | null;
}

export interface ProductResource {
  id: string;
  product_id: string;
  provider_account_id: string | null;
  resource_type: string;
  external_id: string;
  name: string;
  environment: string;
  url: string | null;
  metadata: Record<string, unknown>;
  active: boolean;
}

export interface ProductDetail {
  summary: ProductSummary;
  resources: ProductResource[];
  provider_accounts: ProviderAccount[];
  health_checks: HealthResult[];
}

export interface AuditLog {
  id: string;
  action: string;
  success: boolean;
  error: string | null;
  correlation_id: string | null;
  created_at: string;
  product_id: string | null;
}
