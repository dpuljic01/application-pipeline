"use client";

import { createContext, useCallback, useContext, useMemo, useState } from "react";
import type { ReactNode } from "react";

interface CognitoAuthResult {
  AuthenticationResult?: {
    IdToken: string;
    AccessToken: string;
    ExpiresIn: number;
  };
  message?: string;
  __type?: string;
}

// Cognito's InitiateAuth is a public, unauthenticated REST API — no SDK, no
// signing, just the app client ID. Called directly from the browser.
async function cognitoInitiateAuth(username: string, password: string): Promise<string> {
  const region = process.env.NEXT_PUBLIC_COGNITO_REGION;
  const clientId = process.env.NEXT_PUBLIC_COGNITO_APP_CLIENT_ID;

  const res = await fetch(`https://cognito-idp.${region}.amazonaws.com/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-amz-json-1.1",
      "X-Amz-Target": "AWSCognitoIdentityProviderService.InitiateAuth",
    },
    body: JSON.stringify({
      AuthFlow: "USER_PASSWORD_AUTH",
      ClientId: clientId,
      AuthParameters: { USERNAME: username, PASSWORD: password },
    }),
  });

  const data: CognitoAuthResult = await res.json();

  if (!res.ok || !data.AuthenticationResult) {
    throw new Error(data.message ?? "Sign in failed");
  }

  return data.AuthenticationResult.IdToken;
}

// Display-only — never used for authorization decisions. The backend
// independently verifies the token's signature on every request.
function decodeEmailForDisplay(idToken: string): string | null {
  try {
    const payload = idToken.split(".")[1];
    const padded = payload.padEnd(payload.length + ((4 - (payload.length % 4)) % 4), "=");
    const json = atob(padded.replace(/-/g, "+").replace(/_/g, "/"));
    const claims = JSON.parse(json) as { email?: string };
    return claims.email ?? null;
  } catch {
    return null;
  }
}

interface AuthContextValue {
  idToken: string | null;
  email: string | null;
  isAuthenticated: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  // In-memory only — never localStorage/sessionStorage. Lost on refresh by design.
  const [idToken, setIdToken] = useState<string | null>(null);

  const login = useCallback(async (username: string, password: string) => {
    const token = await cognitoInitiateAuth(username, password);
    setIdToken(token);
  }, []);

  const logout = useCallback(() => {
    setIdToken(null);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      idToken,
      email: idToken ? decodeEmailForDisplay(idToken) : null,
      isAuthenticated: idToken !== null,
      login,
      logout,
    }),
    [idToken, login, logout],
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
