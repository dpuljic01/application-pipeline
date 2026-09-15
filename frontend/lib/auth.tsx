"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { API_BASE_URL } from "@/lib/api";

// Refresh a bit before actual expiry, not right at the edge — avoids a
// request going out with a token that expires mid-flight.
const REFRESH_SKEW_MS = 60_000;

interface CognitoErrorResult {
  message?: string;
  __type?: string;
}

// SignUp/ConfirmSignUp/ResendConfirmationCode carry no tokens, so they stay
// as public, unauthenticated calls straight from the browser to Cognito.
// Login/refresh/logout instead go through the backend below — that's the
// only party that ever sees the refresh token, held in an HttpOnly cookie
// the browser never lets JS read.
async function cognitoRequest<T>(
  action: string,
  body: Record<string, unknown>,
): Promise<T> {
  const region = process.env.NEXT_PUBLIC_COGNITO_REGION;
  const clientId = process.env.NEXT_PUBLIC_COGNITO_APP_CLIENT_ID;

  const res = await fetch(`https://cognito-idp.${region}.amazonaws.com/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-amz-json-1.1",
      "X-Amz-Target": `AWSCognitoIdentityProviderService.${action}`,
    },
    body: JSON.stringify({ ClientId: clientId, ...body }),
  });

  const data = (await res.json()) as T & CognitoErrorResult;

  if (!res.ok) {
    throw new Error(data.message ?? "Request failed");
  }

  return data;
}

export async function signUp(email: string, password: string): Promise<void> {
  await cognitoRequest("SignUp", {
    Username: email,
    Password: password,
    UserAttributes: [{ Name: "email", Value: email }],
  });
}

export async function confirmSignUp(email: string, code: string): Promise<void> {
  await cognitoRequest("ConfirmSignUp", {
    Username: email,
    ConfirmationCode: code,
  });
}

export async function resendSignUpCode(email: string): Promise<void> {
  await cognitoRequest("ResendConfirmationCode", { Username: email });
}

interface TokenResponse {
  id_token: string;
}

async function backendLogin(username: string, password: string): Promise<string> {
  const res = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? "Sign in failed");
  }

  return ((await res.json()) as TokenResponse).id_token;
}

// Returns null on any failure (no cookie, expired, revoked) rather than
// throwing — callers treat "no session" as a normal, expected outcome.
async function backendRefresh(): Promise<string | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: "POST",
      credentials: "include",
    });
    if (!res.ok) return null;
    return ((await res.json()) as TokenResponse).id_token;
  } catch {
    return null;
  }
}

async function backendLogout(): Promise<void> {
  try {
    await fetch(`${API_BASE_URL}/auth/logout`, { method: "POST", credentials: "include" });
  } catch {
    // best-effort — the in-memory token is cleared regardless
  }
}

// Display-only — never used for authorization decisions. The backend
// independently verifies the token's signature on every request.
function decodeClaims(idToken: string): { email: string | null; exp: number | null } {
  try {
    const payload = idToken.split(".")[1];
    const padded = payload.padEnd(payload.length + ((4 - (payload.length % 4)) % 4), "=");
    const json = atob(padded.replace(/-/g, "+").replace(/_/g, "/"));
    const claims = JSON.parse(json) as { email?: string; exp?: number };
    return { email: claims.email ?? null, exp: claims.exp ?? null };
  } catch {
    return { email: null, exp: null };
  }
}

interface AuthContextValue {
  idToken: string | null;
  email: string | null;
  isAuthenticated: boolean;
  isRestoring: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [idToken, setIdToken] = useState<string | null>(null);
  const [isRestoring, setIsRestoring] = useState(true);

  const login = useCallback(async (username: string, password: string) => {
    const token = await backendLogin(username, password);
    setIdToken(token);
  }, []);

  const logout = useCallback(() => {
    setIdToken(null);
    void backendLogout();
  }, []);

  // On mount: an HttpOnly refresh-token cookie (if any) survives a page
  // refresh — ask the backend to trade it for a fresh ID token.
  useEffect(() => {
    let cancelled = false;

    backendRefresh()
      .then((token) => {
        if (!cancelled && token) setIdToken(token);
      })
      .finally(() => {
        if (!cancelled) setIsRestoring(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  // Silently renew shortly before the current ID token expires. Re-fires on
  // its own each time idToken changes, including after this same renewal.
  useEffect(() => {
    if (!idToken) return;

    const { exp } = decodeClaims(idToken);
    if (exp === null) return;

    const delay = Math.max(exp * 1000 - Date.now() - REFRESH_SKEW_MS, 0);
    const timer = setTimeout(async () => {
      setIdToken(await backendRefresh());
    }, delay);

    return () => clearTimeout(timer);
  }, [idToken]);

  const value = useMemo<AuthContextValue>(
    () => ({
      idToken,
      email: idToken ? decodeClaims(idToken).email : null,
      isAuthenticated: idToken !== null,
      isRestoring,
      login,
      logout,
    }),
    [idToken, isRestoring, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
