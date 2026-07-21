"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth-provider";
import { ProtectedPage } from "@/components/protected-page";
import { StatusBadge } from "@/components/status-badge";
import { ErrorState, LoadingState } from "@/components/loading-state";
import { ApiError, apiFetch } from "@/lib/api";
import { relativeTime, shortSha, textValue } from "@/lib/format";
import type { ProductDetail, ProductResource, ProviderResourceSnapshot, UsageMetric } from "@/types/idp";

const tabs = ["Visão geral", "GitHub", "Render", "Supabase", "Documentação", "Auditoria"];

export function ProductDetailView({ slug }: { slug: string }) {
  const { session } = useAuth();
  const [detail, setDetail] = useState<ProductDetail | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [tab, setTab] = useState("Visão geral");
  const [renderSnapshots, setRenderSnapshots] = useState<ProviderResourceSnapshot[] | null>(null);
  const [supabaseSnapshots, setSupabaseSnapshots] = useState<ProviderResourceSnapshot[] | null>(null);
  const [providerError, setProviderError] = useState<string | null>(null);

  useEffect(() => {
    if (!session) return;
    apiFetch<ProductDetail>(session.access_token, `/api/products/${slug}`)
      .then(setDetail)
      .catch((reason) => setError(reason instanceof ApiError ? reason : new ApiError("Falha inesperada.", 500, null)));
  }, [session, slug]);

  useEffect(() => {
    if (!session || !detail) return;
    const productId = detail.summary.id;
    setProviderError(null);
    Promise.allSettled([
      apiFetch<ProviderResourceSnapshot[]>(session.access_token, `/api/products/${productId}/render/services`),
      apiFetch<ProviderResourceSnapshot[]>(session.access_token, `/api/products/${productId}/supabase/projects`),
    ]).then(([renderResult, supabaseResult]) => {
      if (renderResult.status === "fulfilled") setRenderSnapshots(renderResult.value);
      if (supabaseResult.status === "fulfilled") setSupabaseSnapshots(supabaseResult.value);
      if (renderResult.status === "rejected" || supabaseResult.status === "rejected") {
        setProviderError("Não foi possível carregar um dos snapshots de consumo.");
      }
    });
  }, [session, detail]);

  return <ProtectedPage>
    {error ? <ErrorState message={error.message} correlationId={error.correlationId} /> : !detail ? <LoadingState /> : <>
      <section className="page-heading split"><div><p className="eyebrow">Produto</p><h1>{detail.summary.name}</h1><p>{detail.summary.description}</p></div><StatusBadge status={detail.summary.status} /></section>
      <div className="tabs" role="tablist">{tabs.map((item) => <button key={item} role="tab" aria-selected={tab === item} className={tab === item ? "active" : ""} onClick={() => setTab(item)}>{item}</button>)}</div>
      {tab === "Visão geral" ? <Overview detail={detail} /> : null}
      {tab === "GitHub" ? <ResourcePanel title="Repositórios" resources={detail.resources.filter((r) => r.resource_type === "repository")} /> : null}
      {tab === "Render" ? <ProviderUsagePanel title="Serviços Render" resources={detail.resources.filter((r) => r.resource_type === "render_service")} snapshots={renderSnapshots} error={providerError} /> : null}
      {tab === "Supabase" ? <ProviderUsagePanel title="Projetos Supabase" resources={detail.resources.filter((r) => r.resource_type === "supabase_project")} snapshots={supabaseSnapshots} error={providerError} /> : null}
      {tab === "Documentação" ? <ResourcePanel title="Documentação" resources={detail.resources.filter((r) => r.resource_type === "documentation")} /> : null}
      {tab === "Auditoria" ? <section className="panel"><h2>Auditoria</h2><p>Use a tela global de Auditoria para filtrar eventos deste produto.</p></section> : null}
    </>}
  </ProtectedPage>;
}

function ProviderUsagePanel({ title, resources, snapshots, error }: { title: string; resources: ProductResource[]; snapshots: ProviderResourceSnapshot[] | null; error: string | null }) {
  return <section className="panel usage-section">
    <div className="usage-section-heading"><div><h2>{title}</h2><p>Consumo coletado na sincronização mais recente. Aviso em 75% e crítico em 90%.</p></div></div>
    {error ? <p className="inline-warning">{error}</p> : null}
    {!resources.length ? <p>Nenhum recurso cadastrado nesta categoria.</p> : null}
    <div className="usage-resource-list">{resources.map((resource) => {
      const providerResource = snapshots?.find((item) => item.resource_id === resource.id);
      const snapshot = providerResource?.snapshot;
      const usage = snapshot?.usage;
      const providerInfo = snapshot?.service ?? snapshot?.project;
      return <article className="usage-resource" key={resource.id}>
        <header><div><strong>{resource.name}</strong><small>{resource.environment} · plano {providerInfo?.plan ?? String(resource.metadata.plan ?? "não identificado")}</small></div><StatusBadge status={usage?.status === "ok" ? "healthy" : usage?.status === "warning" ? "degraded" : usage?.status === "critical" ? "down" : "unknown"} /></header>
        {!snapshots ? <p>Carregando snapshot de consumo…</p> : !usage ? <p>Sem métricas ainda. Clique em “Sincronizar tudo” para gerar o primeiro snapshot.</p> : <>
          <div className="usage-grid">{usage.metrics.map((metric) => <UsageMetricCard metric={metric} key={metric.key} />)}</div>
          <footer><span>Atualizado {relativeTime(providerResource?.captured_at ?? null)}</span>{providerInfo?.dashboard_url ? <a href={providerInfo.dashboard_url} target="_blank" rel="noreferrer">Abrir painel do provedor ↗</a> : null}</footer>
          {usage.unavailable.length ? <p className="usage-note">Algumas métricas não foram expostas pelo token/API: {usage.unavailable.join(", ")}.</p> : null}
        </>}
      </article>;
    })}</div>
  </section>;
}

export function UsageMetricCard({ metric }: { metric: UsageMetric }) {
  const percentage = metric.percentage == null ? null : Math.min(metric.percentage, 100);
  return <div className={`usage-metric usage-${metric.status}`}>
    <div className="usage-metric-heading"><strong>{metric.label}</strong>{metric.scope !== "resource" ? <span>{scopeLabel(metric.scope)}</span> : null}</div>
    <div className="usage-value">{metric.value == null ? "Uso indisponível" : formatUsageValue(metric.value, metric.unit)}{metric.limit == null ? null : <small> / {formatUsageValue(metric.limit, metric.unit)}</small>}</div>
    {percentage == null ? null : <div className="usage-bar" role="progressbar" aria-label={metric.label} aria-valuenow={metric.percentage ?? undefined} aria-valuemin={0} aria-valuemax={100}><span style={{ width: `${percentage}%` }} /></div>}
    <small>{metric.percentage == null ? metric.description ?? "O provedor não informa uma cota para esta métrica." : `${metric.percentage.toLocaleString("pt-BR")}% utilizado`}</small>
  </div>;
}

function scopeLabel(scope: string) {
  if (scope === "workspace") return "workspace";
  if (scope === "organization") return "organização";
  return scope;
}

function formatUsageValue(value: number, unit: string) {
  if (unit.toLowerCase().includes("byte") || ["b", "kb", "mb", "gb", "kib", "mib", "gib"].includes(unit.toLowerCase())) {
    const multipliers: Record<string, number> = { b: 1, kb: 1_000, mb: 1_000_000, gb: 1_000_000_000, kib: 1024, mib: 1024 ** 2, gib: 1024 ** 3 };
    const bytes = value * (multipliers[unit.toLowerCase()] ?? 1);
    const units = ["B", "KB", "MB", "GB", "TB"];
    let normalized = bytes;
    let index = 0;
    while (normalized >= 1024 && index < units.length - 1) { normalized /= 1024; index += 1; }
    return `${normalized.toLocaleString("pt-BR", { maximumFractionDigits: 1 })} ${units[index]}`;
  }
  return `${value.toLocaleString("pt-BR", { maximumFractionDigits: 2 })} ${unit}`.trim();
}

function Overview({ detail }: { detail: ProductDetail }) {
  const s = detail.summary;
  return <div className="detail-grid">
    <section className="panel"><h2>Resumo operacional</h2><dl className="metric-list large"><div><dt>Último commit</dt><dd>{shortSha(s.last_commit?.sha)}</dd></div><div><dt>Deploy</dt><dd>{textValue(s.last_deploy?.status)}</dd></div><div><dt>CI</dt><dd>{textValue(s.ci?.conclusion ?? s.ci?.status)}</dd></div><div><dt>Última sincronização</dt><dd>{relativeTime(s.last_sync_at)}</dd></div></dl></section>
    <section className="panel"><h2>Conexões</h2><div className="stack-list">{detail.provider_accounts.map((account) => <div key={account.id}><div><strong>{account.name}</strong><small>{account.credential_ref}</small></div><StatusBadge status={account.connection_status} /></div>)}</div></section>
    <section className="panel span-2"><h2>Health checks</h2><div className="table-wrap"><table><thead><tr><th>Nome</th><th>Status</th><th>HTTP</th><th>Latência</th><th>Última verificação</th></tr></thead><tbody>{detail.health_checks.map((health) => <tr key={health.health_check_id}><td>{health.name}</td><td><StatusBadge status={health.status} /></td><td>{health.http_status ?? "—"}</td><td>{health.response_time_ms ? `${health.response_time_ms} ms` : "—"}</td><td>{relativeTime(health.checked_at)}</td></tr>)}</tbody></table></div></section>
  </div>;
}

function ResourcePanel({ title, resources }: { title: string; resources: ProductDetail["resources"] }) {
  return <section className="panel"><h2>{title}</h2>{resources.length ? <div className="table-wrap"><table><thead><tr><th>Nome</th><th>Ambiente</th><th>ID externo</th><th>Ativo</th><th>Link</th></tr></thead><tbody>{resources.map((resource) => <tr key={resource.id}><td>{resource.name}</td><td>{resource.environment}</td><td><code>{resource.external_id}</code></td><td>{resource.active ? "Sim" : "Não"}</td><td>{resource.url ? <a href={resource.url} target="_blank" rel="noreferrer">Abrir ↗</a> : "—"}</td></tr>)}</tbody></table></div> : <p>Nenhum recurso cadastrado nesta categoria.</p>}</section>;
}
