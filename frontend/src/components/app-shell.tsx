"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import { apiFetch } from "@/lib/api";
import { useAuth } from "./auth-provider";

const links = [
  ["/", "Visão geral"],
  ["/products", "Produtos"],
  ["/deploys", "Deploys"],
  ["/health", "Saúde"],
  ["/settings/connections", "Conexões"],
  ["/audit", "Auditoria"],
  ["/settings", "Ajustes"],
] as const;

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { session } = useAuth();
  const [syncing, setSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);

  async function syncAll() {
    if (!session) return;
    setSyncing(true);
    setSyncMessage(null);
    try {
      const run = await apiFetch<{ status: string }>(session.access_token, "/api/sync/all", { method: "POST" });
      setSyncMessage(run.status === "success" ? "Sincronização concluída" : "Sincronização parcial");
      router.refresh();
    } catch (error) {
      setSyncMessage(error instanceof Error ? error.message : "Falha ao sincronizar");
    } finally {
      setSyncing(false);
    }
  }

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="brand"><span className="brand-mark">IDP</span><div><strong>Developer Portal</strong><small>Operações internas</small></div></div>
        <nav aria-label="Navegação principal">
          {links.map(([href, label]) => <Link key={href} href={href} className={pathname === href || (href !== "/" && pathname.startsWith(href)) ? "active" : ""}>{label}</Link>)}
        </nav>
        <div className="sidebar-footer"><small>Acesso</small><strong>Direto, sem login</strong></div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <div><strong>Internal Developer Portal</strong>{syncMessage ? <small>{syncMessage}</small> : <small>Dados servidos por snapshots locais</small>}</div>
          <button className="primary-button" onClick={() => void syncAll()} disabled={syncing}>{syncing ? "Sincronizando…" : "Sincronizar tudo"}</button>
        </header>
        <main className="content">{children}</main>
      </div>
    </div>
  );
}
