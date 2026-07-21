"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth-provider";
import { ProtectedPage } from "@/components/protected-page";
import { StatusBadge } from "@/components/status-badge";
import { ErrorState, LoadingState } from "@/components/loading-state";
import { ApiError, apiFetch } from "@/lib/api";
import { relativeTime, shortSha, textValue } from "@/lib/format";
import type { ProductDetail } from "@/types/idp";

const tabs = ["Visão geral", "GitHub", "Render", "Supabase", "Documentação", "Auditoria"];

export function ProductDetailView({ slug }: { slug: string }) {
  const { session } = useAuth();
  const [detail, setDetail] = useState<ProductDetail | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [tab, setTab] = useState("Visão geral");

  useEffect(() => {
    if (!session) return;
    apiFetch<ProductDetail>(session.access_token, `/api/products/${slug}`)
      .then(setDetail)
      .catch((reason) => setError(reason instanceof ApiError ? reason : new ApiError("Falha inesperada.", 500, null)));
  }, [session, slug]);

  return <ProtectedPage>
    {error ? <ErrorState message={error.message} correlationId={error.correlationId} /> : !detail ? <LoadingState /> : <>
      <section className="page-heading split"><div><p className="eyebrow">Produto</p><h1>{detail.summary.name}</h1><p>{detail.summary.description}</p></div><StatusBadge status={detail.summary.status} /></section>
      <div className="tabs" role="tablist">{tabs.map((item) => <button key={item} role="tab" aria-selected={tab === item} className={tab === item ? "active" : ""} onClick={() => setTab(item)}>{item}</button>)}</div>
      {tab === "Visão geral" ? <Overview detail={detail} /> : null}
      {tab === "GitHub" ? <ResourcePanel title="Repositórios" resources={detail.resources.filter((r) => r.resource_type === "repository")} /> : null}
      {tab === "Render" ? <ResourcePanel title="Serviços Render" resources={detail.resources.filter((r) => r.resource_type === "render_service")} /> : null}
      {tab === "Supabase" ? <ResourcePanel title="Projetos Supabase" resources={detail.resources.filter((r) => r.resource_type === "supabase_project")} /> : null}
      {tab === "Documentação" ? <ResourcePanel title="Documentação" resources={detail.resources.filter((r) => r.resource_type === "documentation")} /> : null}
      {tab === "Auditoria" ? <section className="panel"><h2>Auditoria</h2><p>Use a tela global de Auditoria para filtrar eventos deste produto.</p></section> : null}
    </>}
  </ProtectedPage>;
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
