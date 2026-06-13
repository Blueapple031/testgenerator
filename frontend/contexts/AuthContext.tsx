"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { usePathname, useRouter } from "next/navigation";

import { api, type UserMe } from "@/lib/api";

interface AuthContextValue {
  user: UserMe | null;
  loading: boolean;
  login: (code: string) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

const PUBLIC_PATHS = new Set(["/login"]);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserMe | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  const refresh = useCallback(async () => {
    try {
      const me = await api.get<UserMe>("/auth/me");
      setUser(me);
    } catch {
      setUser(null);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const me = await api.get<UserMe>("/auth/me");
        if (!cancelled) setUser(me);
      } catch {
        if (!cancelled) setUser(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (loading) return;
    if (!user && !PUBLIC_PATHS.has(pathname)) {
      router.replace("/login");
    }
    if (user && pathname === "/login") {
      router.replace("/documents");
    }
  }, [loading, user, pathname, router]);

  const login = useCallback(
    async (code: string) => {
      const res = await api.post<{ user: UserMe }>("/auth/login", { code });
      setUser(res.user);
      router.replace("/documents");
    },
    [router]
  );

  const logout = useCallback(async () => {
    await api.post<void>("/auth/logout");
    setUser(null);
    router.replace("/login");
  }, [router]);

  const value = useMemo(
    () => ({ user, loading, login, logout, refresh }),
    [user, loading, login, logout, refresh]
  );

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-gray-500">
        로딩 중…
      </div>
    );
  }

  if (!user && !PUBLIC_PATHS.has(pathname)) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-gray-500">
        로그인 페이지로 이동 중…
      </div>
    );
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
}

export function formatQuota(user: UserMe): string {
  if (user.token_quota == null) return "무제한";
  const remaining = user.tokens_remaining ?? 0;
  return `${remaining.toLocaleString()} / ${user.token_quota.toLocaleString()}`;
}
