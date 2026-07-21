import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { UsageMetricCard } from "./product-detail";

describe("UsageMetricCard", () => {
  it("shows provider usage and warning threshold", () => {
    render(<UsageMetricCard metric={{
      key: "memory",
      label: "Memória",
      value: 400,
      limit: 500,
      unit: "MB",
      percentage: 80,
      status: "warning",
      scope: "resource",
      period: "24h",
      source: "provider_api",
      description: null,
    }} />);
    expect(screen.getByText("Memória")).toBeInTheDocument();
    expect(screen.getByText("80% utilizado")).toBeInTheDocument();
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "80");
  });

  it("identifies shared plan quotas without inventing usage", () => {
    render(<UsageMetricCard metric={{
      key: "hours",
      label: "Horas grátis",
      value: null,
      limit: 750,
      unit: "h/mês",
      percentage: null,
      status: "unknown",
      scope: "workspace",
      period: "calendar_month",
      source: "plan_limit",
      description: "Cota compartilhada.",
    }} />);
    expect(screen.getByText("workspace")).toBeInTheDocument();
    expect(screen.getByText(/Uso indisponível/)).toBeInTheDocument();
    expect(screen.getByText("Cota compartilhada.")).toBeInTheDocument();
  });
});
