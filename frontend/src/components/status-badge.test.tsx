import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { StatusBadge } from "./status-badge";

describe("StatusBadge", () => {
  it("shows healthy text without relying on color", () => {
    render(<StatusBadge status="healthy" />);
    expect(screen.getByText("Saudável")).toBeInTheDocument();
    expect(screen.getByLabelText("Status: Saudável")).toBeInTheDocument();
  });

  it("shows authentication error explicitly", () => {
    render(<StatusBadge status="authentication_error" />);
    expect(screen.getByText("Falha de autenticação")).toBeInTheDocument();
  });
});
