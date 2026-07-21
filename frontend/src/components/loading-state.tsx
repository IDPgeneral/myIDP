export function LoadingState({ label = "Carregando dados operacionais" }: { label?: string }) {
  return <div className="state-panel loading-panel"><span className="spinner" />{label}…</div>;
}

export function EmptyState({ title, description }: { title: string; description: string }) {
  return <div className="state-panel"><strong>{title}</strong><p>{description}</p></div>;
}

export function ErrorState({ message, correlationId }: { message: string; correlationId?: string | null }) {
  return <div className="state-panel error-panel"><strong>Não foi possível carregar</strong><p>{message}</p>{correlationId ? <small>Correlação: {correlationId}</small> : null}</div>;
}
