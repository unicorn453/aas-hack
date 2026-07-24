import {
  createContext,
  type PropsWithChildren,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import type { AuthStatus, AuthUser } from "../types/auth";
import {
  currentAccessToken,
  initializeKeycloak,
  keycloak,
} from "./keycloak";

interface AuthContextValue {
  status: AuthStatus;
  authenticated: boolean;
  isAdmin: boolean;
  user?: AuthUser;
  error?: string;
  login: () => Promise<void>;
  logout: () => Promise<void>;
  getAccessToken: () => Promise<string>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function readUser(): AuthUser | undefined {
  const token = keycloak.tokenParsed;
  if (!token) return undefined;
  const roles = Array.isArray(token.realm_access?.roles)
    ? token.realm_access.roles
    : [];
  const username =
    (token.preferred_username as string | undefined) ??
    (token.email as string | undefined) ??
    "Authenticated user";
  const displayName =
    (token.name as string | undefined) ??
    [token.given_name, token.family_name].filter(Boolean).join(" ") ??
    username;
  return {
    username,
    displayName: displayName || username,
    email: token.email as string | undefined,
    roles,
  };
}

export function AuthProvider({ children }: PropsWithChildren) {
  const [status, setStatus] = useState<AuthStatus>("initializing");
  const [user, setUser] = useState<AuthUser>();
  const [error, setError] = useState<string>();

  useEffect(() => {
    let active = true;

    initializeKeycloak()
      .then((authenticated) => {
        if (!active) return;
        setUser(authenticated ? readUser() : undefined);
        setStatus(authenticated ? "authenticated" : "anonymous");
      })
      .catch((reason: unknown) => {
        if (!active) return;
        setError(
          reason instanceof Error
            ? reason.message
            : "Authentication service initialization failed.",
        );
        setStatus("error");
      });

    keycloak.onAuthSuccess = () => {
      if (!active) return;
      setUser(readUser());
      setError(undefined);
      setStatus("authenticated");
    };
    keycloak.onAuthLogout = () => {
      if (!active) return;
      setUser(undefined);
      setStatus("anonymous");
    };
    keycloak.onTokenExpired = () => {
      void keycloak.updateToken(30).catch(() => keycloak.clearToken());
    };

    return () => {
      active = false;
    };
  }, []);

  const login = useCallback(async () => {
    setError(undefined);
    await keycloak.login({ redirectUri: window.location.href });
  }, []);

  const logout = useCallback(async () => {
    setStatus("logging-out");
    setUser(undefined);
    await keycloak.logout({ redirectUri: window.location.origin });
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      authenticated: status === "authenticated",
      isAdmin: Boolean(user?.roles.includes("admin")),
      user,
      error,
      login,
      logout,
      getAccessToken: currentAccessToken,
    }),
    [error, login, logout, status, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider.");
  }
  return context;
}
