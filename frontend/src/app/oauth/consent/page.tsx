import { redirect } from "next/navigation";

import { createSupabaseServerClient } from "@/lib/supabase/server";

interface ConsentPageProps {
  searchParams: Promise<{ authorization_id?: string }>;
}

function ErrorCard({ message }: { message: string }) {
  return (
    <main className="login-page">
      <section className="login-card">
        <span className="brand-mark large">IDP</span>
        <p className="eyebrow">Autorização MCP</p>
        <h1>Não foi possível autorizar</h1>
        <p className="form-error">{message}</p>
      </section>
    </main>
  );
}

export default async function ConsentPage({ searchParams }: ConsentPageProps) {
  const authorizationId = (await searchParams).authorization_id?.trim();
  if (!authorizationId || authorizationId.length > 2048) {
    return <ErrorCard message="Solicitação de autorização ausente ou inválida." />;
  }

  const supabase = await createSupabaseServerClient();
  if (!supabase) return <ErrorCard message="Supabase Auth não está configurado." />;
  const { data: claimsData } = await supabase.auth.getClaims();
  if (!claimsData?.claims) {
    const returnPath = `/oauth/consent?authorization_id=${encodeURIComponent(authorizationId)}`;
    redirect(`/login?redirect=${encodeURIComponent(returnPath)}`);
  }

  const { data: details, error } = await supabase.auth.oauth.getAuthorizationDetails(authorizationId);
  if (error || !details) return <ErrorCard message="A solicitação expirou ou não é válida." />;
  if (!("authorization_id" in details)) redirect(details.redirect_url);

  const scopes = details.scope?.split(" ").filter(Boolean) ?? [];
  return (
    <main className="login-page">
      <section className="login-card consent-card">
        <span className="brand-mark large">IDP</span>
        <p className="eyebrow">Autorização MCP</p>
        <h1>Conectar {details.client.name}</h1>
        <p>Este aplicativo poderá consultar produtos, deploys recentes e logs de build do Render.</p>
        <div className="consent-details">
          <strong>Permissões solicitadas</strong>
          <ul>{scopes.map((scope) => <li key={scope}>{scope}</li>)}</ul>
          <small>Somente leitura. Nenhum deploy, restart, rollback ou alteração de variável será permitido.</small>
        </div>
        <form action="/api/oauth/decision" method="post" className="consent-actions">
          <input type="hidden" name="authorization_id" value={authorizationId} />
          <button type="submit" name="decision" value="approve" className="primary-button">Autorizar</button>
          <button type="submit" name="decision" value="deny" className="secondary-button">Negar</button>
        </form>
      </section>
    </main>
  );
}
