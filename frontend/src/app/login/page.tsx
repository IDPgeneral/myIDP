"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { createSupabaseBrowserClient } from "@/lib/supabase/browser";
import { useAuth } from "@/components/auth-provider";

export default function LoginPage() {
  const supabase = useMemo(() => createSupabaseBrowserClient(), []);
  const { session, loading } = useAuth();
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!loading && session) router.replace("/");
  }, [loading, router, session]);

  async function login() {
    setError(null);
    if (!supabase) {
      setError("Supabase Auth não configurado no frontend.");
      return;
    }
    const { error: authError } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: `${window.location.origin}/auth/callback`,
        queryParams: { prompt: "select_account" },
      },
    });
    if (authError) setError("Não foi possível iniciar o login com Google.");
  }

  return (
    <main className="login-page">
      <section className="login-card">
        <span className="brand-mark large">IDP</span>
        <p className="eyebrow">Acesso interno</p>
        <h1>Internal Developer Portal</h1>
        <p>Estado operacional de MILU Software, ColorGlass e Super Excel em um único painel seguro.</p>
        <button className="primary-button wide" onClick={() => void login()} disabled={loading}>Entrar com Google</button>
        {error ? <p className="form-error">{error}</p> : null}
        <small>Somente e-mails previamente autorizados.</small>
      </section>
    </main>
  );
}
