import { useCallback, useEffect, useState } from "react";
import { api, logoutSession } from "../lib/api";
import type { User } from "../lib/types";

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchUser = useCallback(async () => {
    try {
      const u = await api.get<User>("/auth/me");
      setUser(u);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUser();
  }, [fetchUser]);

  const logout = useCallback(async () => {
    try {
      await logoutSession();
    } finally {
      setUser(null);
      window.location.href = "/";
    }
  }, []);

  return { user, loading, logout, refetchUser: fetchUser };
}
