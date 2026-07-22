import { describe, expect, it } from "vitest";

import { safeOAuthReturnPath } from "./oauth";

describe("safeOAuthReturnPath", () => {
  it("keeps only the internal consent route", () => {
    expect(safeOAuthReturnPath("/oauth/consent?authorization_id=auth-123")).toBe(
      "/oauth/consent?authorization_id=auth-123",
    );
  });

  it("rejects external and unrelated redirects", () => {
    expect(safeOAuthReturnPath("https://evil.example/steal")).toBe("/");
    expect(safeOAuthReturnPath("//evil.example/steal")).toBe("/");
    expect(safeOAuthReturnPath("/settings")).toBe("/");
    expect(safeOAuthReturnPath("/oauth/consent")).toBe("/");
  });
});
