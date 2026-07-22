import { NextResponse } from "next/server";

import { createSupabaseServerClient } from "@/lib/supabase/server";

export async function POST(request: Request) {
  const form = await request.formData();
  const authorizationId = String(form.get("authorization_id") ?? "").trim();
  const decision = String(form.get("decision") ?? "");
  if (!authorizationId || authorizationId.length > 2048 || !["approve", "deny"].includes(decision)) {
    return NextResponse.json({ error: "Solicitação inválida." }, { status: 400 });
  }

  const supabase = await createSupabaseServerClient();
  if (!supabase) return NextResponse.json({ error: "Supabase Auth não configurado." }, { status: 503 });
  const { data: claimsData } = await supabase.auth.getClaims();
  if (!claimsData?.claims) return NextResponse.json({ error: "Autenticação obrigatória." }, { status: 401 });

  const result = decision === "approve"
    ? await supabase.auth.oauth.approveAuthorization(authorizationId)
    : await supabase.auth.oauth.denyAuthorization(authorizationId);
  if (result.error || !result.data?.redirect_url) {
    return NextResponse.json({ error: "Não foi possível concluir a autorização." }, { status: 400 });
  }
  return NextResponse.redirect(result.data.redirect_url, 303);
}
