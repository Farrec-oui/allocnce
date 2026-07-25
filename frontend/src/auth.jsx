import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api, setUnauthorizedHandler } from "./api";

const TOKEN_KEY = "allocnce_token";
const USER_KEY = "allocnce_user";

const AuthContext = createContext(null);

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

function readStoredUser() {
  try {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(readStoredUser);
  // `loading` couvre la revalidation du token au démarrage : sans ça, un token
  // expiré laisserait brièvement voir l'application avant la redirection.
  const [loading, setLoading] = useState(() => Boolean(getToken()));

  const persist = useCallback((token, nextUser) => {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USER_KEY, JSON.stringify(nextUser));
    setUser(nextUser);
  }, []);

  const clear = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    setUser(null);
  }, []);

  // Une 401 renvoyée par n'importe quel appel API purge la session.
  useEffect(() => {
    setUnauthorizedHandler(clear);
    return () => setUnauthorizedHandler(null);
  }, [clear]);

  // Au démarrage, vérifier que le token stocké est toujours valide.
  useEffect(() => {
    if (!getToken()) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const me = await api.me();
        if (!cancelled) {
          localStorage.setItem(USER_KEY, JSON.stringify(me));
          setUser(me);
        }
      } catch {
        if (!cancelled) clear();
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [clear]);

  const login = useCallback(async (email, password) => {
    const data = await api.login(email, password);
    persist(data.access_token, data.user);
    return data.user;
  }, [persist]);

  const register = useCallback(async (payload) => {
    const data = await api.register(payload);
    persist(data.access_token, data.user);
    return data.user;
  }, [persist]);

  const logout = useCallback(async () => {
    try {
      await api.logout();
    } catch {
      // Le token est peut-être déjà expiré — on purge quand même.
    }
    clear();
  }, [clear]);

  const updateProfile = useCallback(async (payload) => {
    const me = await api.updateMe(payload);
    localStorage.setItem(USER_KEY, JSON.stringify(me));
    setUser(me);
    return me;
  }, []);

  const value = useMemo(() => ({
    user,
    loading,
    isAuthenticated: Boolean(user),
    isAdmin: user?.role === "admin",
    login,
    register,
    logout,
    updateProfile,
  }), [user, loading, login, register, logout, updateProfile]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth doit être utilisé dans un <AuthProvider>");
  return ctx;
}
