"use client";

import { createContext, useContext } from "react";

interface DirectSession {
  access_token: string;
}

interface DirectUser {
  email: string;
}

interface AuthContextValue {
  session: DirectSession;
  user: DirectUser;
  loading: boolean;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);
const directAccess: AuthContextValue = {
  session: { access_token: "" },
  user: { email: "Acesso direto" },
  loading: false,
  signOut: async () => undefined,
};

export function AuthProvider({ children }: { children: React.ReactNode }) {
  return <AuthContext.Provider value={directAccess}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth deve ser usado dentro de AuthProvider.");
  return context;
}
