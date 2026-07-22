"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth-provider";
import { ProtectedPage } from "@/components/protected-page";
import { StatusBadge } from "@/components/status-badge";
import { ErrorState, LoadingState } from "@/components/loading-state";
import { ApiError, apiFetch } from "@/lib/api";
import { relativeTime, shortSha, textValue } from "@/lib/format";
import type { HealthResult, ProductDetail, ProductResource, ProviderResourceSnapshot, RenderDeploy, UsageMetric } from "@/types/idp";

const tabs = ["Visão geral", "GitHub", "Render", "Supabase", "Documentação", "Auditoria"];

export function ProductDetailView({ slug }: { slug: string }) {
  const { session } = useAuth();
  const [detail, setDetail] = useState<ProductDetail | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [tab, setTab] = useState("Visão geral");
  const [renderSnapshots, setRenderSnapshots] = useState<ProviderResourceSnapshot[] | null>(null);
  const [supabaseSnapshots, setSupabaseSnapshots] = useState<ProviderResourceSnapshot[] | null>(null);
  const [providerError, setProviderError] = useState<string | null>(null);
  const [syncingProduct, setSyncingProduct] = useState(false);
  const [runningHealth, setRunningHealth] = useState(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!session) return;
    apiFetch<ProductDetail>(session.access_token, `/api/products/${slug}`)
      .then(setDetail)
      .catch((reason) => setError(reason instanceof ApiError ? reason : new ApiError("Falha inesperada.", 500, null)));
  }, [session, slug]);

  useEffect(() => {
    if (!session || !detail) return;
    const productId = detail.summary.id;
    Promise.allSettled([
      apiFetch<ProviderResourceSnapshot[]>(session.access_token, `/api/products/${productId}/render/services`),
      apiFetch<ProviderResourceSnapshot[]>(session.access_token, `/api/products/${productId}/supabase/projects`),
    ]).then(([renderResult, supabaseResult]) => {
      setProviderError(null);
      if (renderResult.status === "fulfilled") setRenderSnapshots(renderResult.value);
      if (supabaseResult.status === "fulfilled") setSupabaseSnapshots(supabaseResult.value);
      if (renderResult.status === "rejected" || supabaseResult.status === "rejected") {
        setProviderError("Não foi possível carregar um dos snapshots de consumo.");
      }
    });
  }, [session, detail]);

  async function syncProduct() {
    if (!session || !detail) return;
    setSyncingProduct(true);
    setActionMessage(null);
    try {
      const run = await apiFetch<{ status: string }>(session.access_token, `/api/sync/products/${detail.summary.id}`, { method: "POST" });
      setActionMessage(run.status === "success" ? "Produto sincronizado." : "Sincronização concluída com avisos.");
      const updated = await apiFetch<ProductDetail>(session.access_token, `/api/products/${slug}`);
      setDetail(updated);
    } catch (reason) {
      setActionMessage(reason instanceof Error ? reason.message : "Falha ao sincronizar o produto.");
    } finally {
      setSyncingProduct(false);
    }
  }

  async function runAllHealthChecks() {
    if (!session || !detail) return;
    setRunningHealth(true);
    setActionMessage(null);
    try {
      const result = await apiFetch<{ checks: HealthResult[] }>(session.access_token, `/api/products/${detail.summary.id}/health/run`, { method: "POST" });
      setDetail({ ...detail, health_checks: result.checks });
      const failures = result.checks.filter((item) => item.status !== "healthy").length;
      setActionMessage(failures ? `${failures} health check(s) requerem atenção.` : `${result.checks.length} health check(s) saudáveis.`);
    } catch (reason) {
      setActionMessage(reason instanceof Error ? reason.message : "Falha ao executar health checks.");
    } finally {
      setRunningHealth(false);
    }
  }

  return <ProtectedPage>
    {error ? <ErrorState message={error.message} correlationId={error.correlationId} /> : !detail ? <LoadingState /> : <>
      <section className="page-heading split"><div><p className="eyebrow">Produto</p><h1>{detail.summary.name}</h1><p>{detail.summary.description}</p>{actionMessage ? <p className="action-feedback" role="status">{actionMessage}</p> : null}</div><div className="page-actions"><StatusBadge status={detail.summary.status} /><button className="secondary-button" onClick={() => void runAllHealthChecks()} disabled={runningHealth}>{runningHealth ? "Verificando…" : "Executar health checks"}</button><button className="primary-button" onClick={() => void syncProduct()} disabled={syncingProduct}>{syncingProduct ? "Sincronizando…" : "Sincronizar produto"}</button></div></section>
      <div className="tabs" role="tablist">{tabs.map((item) => <button key={item} role="tab" aria-selected={tab === item} className={tab === item ? "active" : ""} onClick={() => setTab(item)}>{item}</button>)}</div>
      {tab === "Visão geral" ? <Overview detail={detail} /> : null}
      {tab === "GitHub" ? <ResourcePanel title="Repositórios" resources={detail.resources.filter((r) => r.resource_type === "repository")} /> : null}
      {tab === "Render" ? <RenderOperationsPanel resources={detail.resources.filter((r) => r.resource_type === "render_service")} snapshots={renderSnapshots} error={providerError} token={session?.access_token ?? ""} productId={detail.summary.id} /> : null}
      {tab === "Supabase" ? <ProviderUsagePanel title="Projetos Supabase" resources={detail.resources.filter((r) => r.resource_type === "supabase_project")} snapshots={supabaseSnapshots} error={providerError} /> : null}
      {tab === "Documentação" ? <ResourcePanel title="Documentação" resources={detail.resources.filter((r) => r.resource_type === "documentation")} /> : null}
      {tab === "Auditoria" ? <section className="panel"><h2>Auditoria</h2><p>Use a tela global de Auditoria para filtrar eventos deste produto.</p></section> : null}
    </>}
  </ProtectedPage>;
}

type OperationState = {
  pending: boolean;
  status: string;
  message: string;
};

function RenderOperationsPanel({ resources, snapshots, error, token, productId }: { resources: ProductResource[]; snapshots: ProviderResourceSnapshot[] | null; error: string | null; token: string; productId: string }) {
  const [commits, setCommits] = useState<Record<string, string>>({});
  const [clearCache, setClearCache] = useState<Record<string, boolean>>({});
  const [operations, setOperations] = useState<Record<string, OperationState>>({});

  function updateOperation(resourceId: string, changes: Partial<OperationState>) {
    setOperations((current) => ({
      ...current,
      [resourceId]: {
        pending: current[resourceId]?.pending ?? false,
        status: current[resourceId]?.status ?? "idle",
        message: current[resourceId]?.message ?? "",
        ...changes,
      },
    }));
  }

  async function deploy(resource: ProductResource) {
    const commitId = commits[resource.id]?.trim() || null;
    const target = commitId ? `o commit ${commitId}` : "o último commit da branch configurada";
    if (!window.confirm(`Confirmar deploy de ${resource.name} usando ${target}?`)) return;
    updateOperation(resource.id, { pending: true, status: "queued", message: "Solicitando deploy ao Render…" });
    try {
      const response = await apiFetch<{ result: unknown }>(token, `/api/render/services/${resource.id}/deploy`, {
        method: "POST",
        body: JSON.stringify({ confirmation: "CONFIRMAR", commit_id: commitId, clear_cache: Boolean(clearCache[resource.id]) }),
      });
      const deployId = findDeployId(response.result);
      if (!deployId) {
        updateOperation(resource.id, { pending: false, status: "accepted", message: "Deploy aceito. Sincronize o produto para atualizar o snapshot." });
        return;
      }
      updateOperation(resource.id, { status: "queued", message: `Deploy ${deployId} enfileirado.` });
      await followDeploy(resource, deployId);
    } catch (reason) {
      updateOperation(resource.id, { pending: false, status: "error", message: reason instanceof Error ? reason.message : "Falha ao iniciar deploy." });
    }
  }

  async function followDeploy(resource: ProductResource, deployId: string) {
    const terminal = new Set(["live", "build_failed", "update_failed", "canceled", "deactivated"]);
    for (let attempt = 0; attempt < 60; attempt += 1) {
      if (attempt > 0) await delay(5000);
      const response = await apiFetch<unknown>(token, `/api/render/services/${resource.id}/deploys/${deployId}/status`);
      const deploy = normalizeDeploy(response);
      const status = deploy.status ?? "unknown";
      updateOperation(resource.id, { pending: !terminal.has(status), status, message: deployStatusMessage(status) });
      if (!terminal.has(status)) continue;
      await apiFetch(token, `/api/sync/resources/${resource.id}`, { method: "POST" }).catch(() => null);
      if (status === "live") {
        const health = await apiFetch<{ checks: HealthResult[] }>(token, `/api/products/${productId}/health/run`, { method: "POST" }).catch(() => null);
        const failures = health?.checks.filter((item) => item.status !== "healthy").length ?? 0;
        updateOperation(resource.id, {
          pending: false,
          status: failures ? "degraded" : "live",
          message: failures ? `Deploy publicado, mas ${failures} health check(s) falharam.` : "Deploy publicado e health checks concluídos.",
        });
      }
      return;
    }
    updateOperation(resource.id, { pending: false, status: "timeout", message: "O deploy continua em andamento. Sincronize novamente em alguns minutos." });
  }

  async function restart(resource: ProductResource) {
    if (!window.confirm(`Confirmar reinício de ${resource.name}?`)) return;
    updateOperation(resource.id, { pending: true, status: "restarting", message: "Solicitando reinício ao Render…" });
    try {
      await apiFetch(token, `/api/render/services/${resource.id}/restart`, { method: "POST", body: JSON.stringify({ confirmation: "CONFIRMAR" }) });
      updateOperation(resource.id, { pending: false, status: "accepted", message: "Reinício aceito pelo Render." });
    } catch (reason) {
      updateOperation(resource.id, { pending: false, status: "error", message: reason instanceof Error ? reason.message : "Falha ao reiniciar serviço." });
    }
  }

  return <section className="panel usage-section">
    <div className="usage-section-heading"><div><h2>Central de operações Render</h2><p>Deploy por commit, limpeza de cache, reinício e acompanhamento até os health checks.</p></div></div>
    {error ? <p className="inline-warning">{error}</p> : null}
    {!resources.length ? <p>Nenhum serviço Render cadastrado.</p> : null}
    <div className="usage-resource-list">{resources.map((resource) => {
      const providerResource = snapshots?.find((item) => item.resource_id === resource.id);
      const snapshot = providerResource?.snapshot;
      const usage = snapshot?.usage;
      const service = snapshot?.service;
      const operation = operations[resource.id];
      const recentDeploys = snapshot?.recent_deploys ?? [];
      return <article className="usage-resource operation-card" key={resource.id}>
        <header><div><strong>{resource.name}</strong><small>{resource.environment} · branch {service?.branch ?? "não identificada"} · plano {service?.plan ?? String(resource.metadata.plan ?? "não identificado")}</small></div><StatusBadge status={renderServiceStatus(operation?.status, snapshot?.last_deploy?.status)} /></header>
        <div className="operation-summary">
          <div><span>Deploy atual</span><strong>{snapshot?.last_deploy?.status ?? "sem snapshot"}</strong></div>
          <div><span>Commit atual</span><strong><code>{deployCommit(snapshot?.last_deploy) ?? "—"}</code></strong></div>
          <div><span>Atualizado</span><strong>{relativeTime(providerResource?.captured_at ?? null)}</strong></div>
        </div>
        <div className="deploy-controls">
          <label><span>Commit específico (opcional)</span><input value={commits[resource.id] ?? ""} onChange={(event) => setCommits((current) => ({ ...current, [resource.id]: event.target.value }))} placeholder="SHA do commit; vazio usa o mais recente" /></label>
          <label className="checkbox-control"><input type="checkbox" checked={Boolean(clearCache[resource.id])} onChange={(event) => setClearCache((current) => ({ ...current, [resource.id]: event.target.checked }))} /><span>Limpar cache antes do build</span></label>
          <div className="operation-buttons"><button className="primary-button" disabled={operation?.pending} onClick={() => void deploy(resource)}>Fazer deploy</button><button className="secondary-button danger-button" disabled={operation?.pending} onClick={() => void restart(resource)}>Reiniciar</button>{service?.dashboard_url ? <a className="secondary-button" href={service.dashboard_url} target="_blank" rel="noreferrer">Abrir Render ↗</a> : null}</div>
        </div>
        {operation?.message ? <p className={`operation-message operation-${operation.status}`} role="status">{operation.pending ? <span className="mini-spinner" /> : null}{operation.message}</p> : null}
        {recentDeploys.length ? <details className="deploy-history"><summary>Deploys recentes</summary><div className="table-wrap"><table><thead><tr><th>Status</th><th>Commit</th><th>Quando</th><th>Ação</th></tr></thead><tbody>{recentDeploys.slice(0, 5).map((item, index) => { const commit = deployCommit(item); return <tr key={item.id ?? index}><td>{item.status ?? "—"}</td><td><code>{commit ?? "—"}</code></td><td>{relativeTime(item.created_at ?? null)}</td><td>{commit ? <button className="table-action" onClick={() => setCommits((current) => ({ ...current, [resource.id]: commit }))}>Selecionar</button> : "—"}</td></tr>; })}</tbody></table></div></details> : null}
        {usage ? <><div className="usage-grid compact-usage">{usage.metrics.map((metric) => <UsageMetricCard metric={metric} key={metric.key} />)}</div>{usage.unavailable.length ? <p className="usage-note">Métricas não expostas: {usage.unavailable.join(", ")}.</p> : null}</> : <p>Sem métricas ainda. Sincronize o produto para gerar o snapshot.</p>}
      </article>;
    })}</div>
  </section>;
}

function findDeployId(payload: unknown): string | null {
  const deploy = normalizeDeploy(payload);
  return typeof deploy.id === "string" ? deploy.id : null;
}

function normalizeDeploy(payload: unknown): RenderDeploy {
  if (!payload || typeof payload !== "object") return {};
  const data = payload as Record<string, unknown>;
  const nested = data.deploy;
  return nested && typeof nested === "object" ? nested as RenderDeploy : data as RenderDeploy;
}

function deployCommit(deploy?: RenderDeploy | null): string | null {
  if (!deploy?.commit) return null;
  if (typeof deploy.commit === "string") return deploy.commit;
  return deploy.commit.id ?? null;
}

function renderServiceStatus(operationStatus?: string, deployStatus?: string) {
  const status = operationStatus ?? deployStatus ?? "unknown";
  if (status === "live") return "healthy";
  if (["build_failed", "update_failed", "canceled", "error"].includes(status)) return "down";
  if (["queued", "build_in_progress", "update_in_progress", "pre_deploy_in_progress", "restarting"].includes(status)) return "syncing";
  return status;
}

function deployStatusMessage(status: string) {
  const messages: Record<string, string> = {
    queued: "Deploy aguardando na fila do Render…",
    build_in_progress: "Build em andamento…",
    pre_deploy_in_progress: "Executando etapa anterior ao deploy…",
    update_in_progress: "Publicando a nova versão…",
    live: "Deploy publicado. Executando health checks…",
    build_failed: "O build falhou no Render.",
    update_failed: "O Render não conseguiu publicar a versão.",
    canceled: "Deploy cancelado.",
    deactivated: "Deploy desativado.",
  };
  return messages[status] ?? `Estado do deploy: ${status}.`;
}

function delay(milliseconds: number) {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
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
