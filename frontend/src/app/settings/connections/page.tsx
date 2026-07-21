"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth-provider";
import { ProtectedPage } from "@/components/protected-page";
import { StatusBadge } from "@/components/status-badge";
import { ErrorState, LoadingState } from "@/components/loading-state";
import { ApiError, apiFetch } from "@/lib/api";
import { relativeTime } from "@/lib/format";
import type { ProviderAccount } from "@/types/idp";

export default function ConnectionsPage() {
  const { session } = useAuth();
  const [accounts, setAccounts] = useState<ProviderAccount[] | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  useEffect(() => { if (session) apiFetch<ProviderAccount[]>(session.access_token, "/api/provider-accounts").then(setAccounts).catch((e) => setError(e)); }, [session]);
  return <ProtectedPage><section className="page-heading"><div><p className="eyebrow">Ajustes</p><h1>Conexões</h1><p>As credenciais nunca são exibidas; somente a referência e o estado da validação.</p></div></section>{error ? <ErrorState message={error.message} correlationId={error.correlationId} /> : !accounts ? <LoadingState /> : <section className="panel"><div className="table-wrap"><table><thead><tr><th>Conexão</th><th>Provedor</th><th>Status</th><th>Variável esperada</th><th>Configurada</th><th>Última sincronização</th><th>Erro</th></tr></thead><tbody>{accounts.map((account) => <tr key={account.id}><td><strong>{account.name}</strong></td><td>{account.provider}</td><td><StatusBadge status={account.connection_status} /></td><td><code>{account.credential_ref}</code></td><td>{account.credential_configured ? "Sim" : "Não"}</td><td>{relativeTime(account.last_sync_at)}</td><td>{account.last_error ?? "—"}</td></tr>)}</tbody></table></div></section>}</ProtectedPage>;
}
