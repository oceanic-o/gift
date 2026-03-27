/**
 * src/lib/store/auth.tsx
 * Global auth state — wraps the whole app.
 * Persists user info in localStorage so page refresh keeps you logged in.
 */
import {
  createContext,
  useContext,
  useState,
  useEffect,
  ReactNode,
} from "react";
import { clearToken, getToken } from "../api/client";

interface AuthUser {
  id: number;
  name: string;
  email: string;
  role: "user" | "admin";
  provider?: string | null;
  google_sub?: string | null;
  avatar_url?: string | null;
  given_name?: string | null;
  family_name?: string | null;
  locale?: string | null;
}

interface AuthCtx {
  user: AuthUser | null;
  isLoggedIn: boolean;
  isAdmin: boolean;
  setUser: (u: AuthUser | null) => void;
  logout: () => void;
}

const Ctx = createContext<AuthCtx>({
  user: null,
  isLoggedIn: false,
  isAdmin: false,
  setUser: () => {},
  logout: () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUserState] = useState<AuthUser | null>(() => {
    try {
      return JSON.parse(localStorage.getItem("auth_user") ?? "null");
    } catch {
      return null;
    }
  });

  // If token is gone on load, clear stored user too
  useEffect(() => {
    if (!getToken()) {
      setUserState(null);
      localStorage.removeItem("auth_user");
    }
  }, []);

  // Listen for forced logout from API client (expired token)
  useEffect(() => {
    const handler = () => {
      setUserState(null);
    };
    window.addEventListener("auth:logout", handler);
    return () => window.removeEventListener("auth:logout", handler);
  }, []);

  const setUser = (u: AuthUser | null) => {
    setUserState(u);
    if (u) localStorage.setItem("auth_user", JSON.stringify(u));
    else localStorage.removeItem("auth_user");
  };

  const logout = () => {
    clearToken();
    setUser(null);
  };

  return (
    <Ctx.Provider
      value={{
        user,
        isLoggedIn: !!user,
        isAdmin: user?.role === "admin",
        setUser,
        logout,
      }}
    >
      {children}
    </Ctx.Provider>
  );
}

export const useAuth = () => useContext(Ctx);
