const LOCAL_ORIGIN = "https://idp.local";

export function safeOAuthReturnPath(value: string | null | undefined): string {
  if (!value || value.length > 2400 || !value.startsWith("/")) return "/";
  try {
    const parsed = new URL(value, LOCAL_ORIGIN);
    const authorizationId = parsed.searchParams.get("authorization_id");
    if (
      parsed.origin !== LOCAL_ORIGIN ||
      parsed.pathname !== "/oauth/consent" ||
      !authorizationId ||
      authorizationId.length > 2048
    ) {
      return "/";
    }
    return `${parsed.pathname}?authorization_id=${encodeURIComponent(authorizationId)}`;
  } catch {
    return "/";
  }
}
