"use client";

import { createContext, useCallback, useContext, useMemo, useState } from "react";
import type { ReactNode } from "react";

interface CognitoErrorResult {
  message?: string;
  __type?: string;
}

// Cognito's identity-provider actions (InitiateAuth, SignUp, ConfirmSignUp,
// ...) are all public, unauthenticated REST calls — no SDK, no signing, just
// the app client ID. Called directly from the browser for all of them.
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
    // Cognito's own message is specific ("Password did not conform with
    // policy...", "User already exists", "Invalid verification code...") —
    // surface it as-is rather than a generic failure string.
    throw new Error(data.message ?? "Request failed");
  }

  return data;
}

async function cognitoInitiateAuth(username: string, password: string): Promise<string> {
  const data = await cognitoRequest<{
    AuthenticationResult?: { IdToken: string; AccessToken: string; ExpiresIn: number };
  }>("InitiateAuth", {
    AuthFlow: "USER_PASSWORD_AUTH",
    AuthParameters: { USERNAME: username, PASSWORD: password },
  });

  if (!data.AuthenticationResult) {
    throw new Error("Sign in failed");
  }

  return data.AuthenticationResult.IdToken;
}

// Self-service registration — the two Cognito calls a new user needs before
// they can sign in: create the account, then confirm it with the emailed
// code. Standalone (not part of AuthContext) since neither one produces a
// signed-in session by itself.
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
