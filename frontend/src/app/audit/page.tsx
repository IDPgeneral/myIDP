"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth-provider";
import { ProtectedPage } from "@/components/protected-page";
import { ErrorState, LoadingState } from "@/components/loading-state";
import { ApiError, apiFetch } from "@/lib/api";
import { relativeTime } from "@/lib/format";
import type { AuditLog } from "@/types/idp";

export default function AuditPage() {
  const { session } = useAuth();
  const [logs, setLogs] = useState<AuditLog[] | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  useEffect(() => { if (session) apiFetch<AuditLog[]>(session.access_token, "/api/audit-logs?limit=200").then(setLogs).catch((e) => setError(e)); }, [session]);
  return <ProtectedPage><section className="page-heading"><div><p className="eyebrow">Rastreabilidade</p><h1>Auditoria</h1><p>Sincronizações, testes de conexão e ações operacionais com correlation ID.</p></div></section>{error ? <ErrorState message={error.message} correlationId={error.correlationId} /> : !logs ? <LoadingState /> : <section className="panel"><div className="table-wrap"><table><thead><tr><th>Quando</th><th>Ação</th><th>Resultado</th><th>Produto</th><th>Erro</th><th>Correlação</th></tr></thead><tbody>{logs.map((log) => <tr key={log.id}><td>{relativeTime(log.created_at)}</td><td><code>{log.action}</code></td><td>{log.success ? "Sucesso" : "Falha"}</td><td>{log.product_id ?? "—"}</td><td>{log.error ?? "—"}</td><td><code>{log.correlation_id ?? "—"}</code></td></tr>)}</tbody></table></div></section>}</ProtectedPage>;
}
