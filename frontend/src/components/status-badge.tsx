const labels: Record<string, string> = {
  healthy: "Saudável",
  connected: "Conectado",
  degraded: "Atenção",
  down: "Indisponível",
  error: "Erro",
  authentication_error: "Falha de autenticação",
  permission_error: "Sem permissão",
  provider_unavailable: "Provedor indisponível",
  not_configured: "Não configurado",
  syncing: "Sincronizando",
  unknown: "Desconhecido",
};

export function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`status-badge status-${status}`} aria-label={`Status: ${labels[status] ?? status}`}>
      <span className="status-dot" aria-hidden="true" />
      {labels[status] ?? status}
    </span>
  );
}
