"use client";
import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "./api";
import type { Me, Role } from "./types";

interface AuthCtx {
  me: Me | null;
  loading: boolean;
  refresh: () => Promise<Me | null>;
  logout: () => Promise<void>;
  setMe: (m: Me | null) => void;
}
const Ctx = createContext<AuthCtx>({ me: null, loading: true, refresh: async () => null, logout: async () => {}, setMe: () => {} });
export const useAuth = () => useContext(Ctx);

export const homeFor = (role: Role) => (role === "customer" ? "/portal" : role === "provider" ? "/provider" : "/admin");

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [me, setMe] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const m = await api<Me>("/auth/me");
      setMe(m);
      return m;
    } catch (e) {
      if (!(e instanceof ApiError) || e.status !== 401) console.error(e);
      setMe(null);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const logout = useCallback(async () => {
    try { await api("/auth/logout", { method: "POST", body: {} }); } catch { /* already signed out */ }
    setMe(null);
  }, []);

  return <Ctx.Provider value={{ me, loading, refresh, logout, setMe }}>{children}</Ctx.Provider>;
}

/** Client-side route guard. Real authorisation is always enforced by the API. */
export function RequireRole({ roles, children }: { roles: Role[]; children: React.ReactNode }) {
  const { me, loading } = useAuth();
  const router = useRouter();
  const allowed = !!me && roles.includes(me.role) && !(me.mfa_required);

  useEffect(() => {
    if (loading) return;
    if (!me) router.replace("/login");
    else if (me.mfa_required) router.replace("/login");
    else if (!roles.includes(me.role)) router.replace(homeFor(me.role));
  }, [me, loading, roles, router]);

  if (loading || !allowed) return <div className="p-10 text-center text-sm text-muted-foreground">Loading…</div>;
  return <>{children}</>;
}
