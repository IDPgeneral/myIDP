import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ProductCard } from "./product-card";
import type { ProductSummary } from "@/types/idp";

const base: ProductSummary = {
  id: "1", name: "MILU Software", slug: "milu-software", description: "Produto", owner: "owner", status: "healthy",
  github_status: "connected", render_status: "connected", supabase_status: "connected", last_commit: { sha: "fc1b348999" },
  last_deploy: { status: "live" }, ci: { conclusion: "success" }, health: { health_check_id: "h", name: "backend", status: "healthy", http_status: 200, response_time_ms: 80, message: "200 OK", checked_at: null },
  last_sync_at: null, alert_count: 0,
};

describe("ProductCard", () => {
  it("renders a healthy product dashboard card", () => {
    render(<ProductCard product={base} />);
    expect(screen.getByText("MILU Software")).toBeInTheDocument();
    expect(screen.getByText("fc1b348")).toBeInTheDocument();
    expect(screen.getByText("200 · healthy")).toBeInTheDocument();
  });

  it("renders degraded state and alerts", () => {
    render(<ProductCard product={{ ...base, status: "degraded", render_status: "authentication_error", alert_count: 2 }} />);
    expect(screen.getByText("Atenção")).toBeInTheDocument();
    expect(screen.getByText("2 alerta(s)")).toBeInTheDocument();
    expect(screen.getByText("Falha de autenticação")).toBeInTheDocument();
  });
});
