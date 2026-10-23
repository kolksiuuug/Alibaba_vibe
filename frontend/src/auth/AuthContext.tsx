import { useQueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

import { setUnauthorizedHandler, tokenStore, type Schemas } from "../api/client";
import { Api } from "../api/endpoints";

type User = Schemas["User"];

interface AuthValue {
  user: User | null;
  loading: boolean;
  loginAs: (login: string) => Promise<User>;
  logout: () => void;
}

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const logout = useCallback(() => {
    tokenStore.clear();
    queryClient.clear();
    setUser(null);
  }, [queryClient]);

  useEffect(() => {
    setUnauthorizedHandler(logout);
    if (!tokenStore.get()) {
      setLoading(false);
      return;
    }
    Api.me()
      .then(setUser)
      .catch(() => tokenStore.clear())
      .finally(() => setLoading(false));
  }, [logout]);

  const loginAs = useCallback(
    async (login: string) => {
      const { token, user: next } = await Api.login(login);
      tokenStore.set(token);
      queryClient.clear();
      setUser(next);
      return next;
    },
    [queryClient],
  );

  const value = useMemo(
    () => ({ user, loading, loginAs, logout }),
    [user, loading, loginAs, logout],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth вне AuthProvider");
  return value;
}

export function homePath(user: User | null): string {
  return user?.role === "analyst" ? "/analyst" : "/";
}
