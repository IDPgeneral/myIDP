"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "./auth-provider";
import { LoadingState } from "./loading-state";
import { AppShell } from "./app-shell";

export function ProtectedPage({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { session, loading } = useAuth();
  useEffect(() => {
    if (!loading && !session) router.replace("/login");
  }, [loading, router, session]);
  if (loading || !session) return <div className="centered-page"><LoadingState label="Validando sessão" /></div>;
  return <AppShell>{children}</AppShell>;
}
