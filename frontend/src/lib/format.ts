export function relativeTime(value: string | null): string {
  if (!value) return "Nunca";
  const delta = Date.now() - new Date(value).getTime();
  const minutes = Math.max(0, Math.round(delta / 60_000));
  if (minutes < 1) return "Agora";
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} h`;
  return new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" }).format(new Date(value));
}

export function shortSha(value: unknown): string {
  return typeof value === "string" && value ? value.slice(0, 7) : "—";
}

export function textValue(value: unknown, fallback = "—"): string {
  return typeof value === "string" && value ? value : fallback;
}
