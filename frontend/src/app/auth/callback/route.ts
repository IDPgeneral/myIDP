import { NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/lib/supabase/server";
import { safeOAuthReturnPath } from "@/lib/oauth";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const forwardedHost = request.headers.get("x-forwarded-host");
  const forwardedProto = request.headers.get("x-forwarded-proto") ?? "https";
  const publicOrigin = forwardedHost ? `${forwardedProto}://${forwardedHost}` : url.origin;
  const code = url.searchParams.get("code");
  const next = safeOAuthReturnPath(url.searchParams.get("next"));
  if (!code) return NextResponse.redirect(new URL("/login", publicOrigin));

  const supabase = await createSupabaseServerClient();
  if (!supabase) return NextResponse.redirect(new URL("/login?error=config", publicOrigin));
  const { error } = await supabase.auth.exchangeCodeForSession(code);
  if (error) return NextResponse.redirect(new URL("/login?error=callback", publicOrigin));
  return NextResponse.redirect(new URL(next, publicOrigin));
}
