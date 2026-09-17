"use client";

import { useState } from "react";
import type { FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { MagneticDots } from "@/components/magnetic-dots";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [status, setStatus] = useState<"idle" | "authenticating" | "error">("idle");
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setStatus("authenticating");
    setError(null);
    try {
      await login(username, password);
      router.push("/");
    } catch (err) {
      setStatus("error");
      setError(err instanceof Error ? err.message : "Sign in failed");
    }
  }

  return (
    <div className="relative flex min-h-screen flex-1 items-center justify-center overflow-hidden bg-background px-4">
      <MagneticDots />
      <div className="relative z-10 w-full max-w-sm">
        <div className="mb-8 text-center">
          <p className="font-mono text-base font-medium tracking-[0.15em] text-foreground uppercase">
            Job Dossier
          </p>
          <div className="mx-auto mt-3 h-px w-10 bg-border" />
        </div>

        <form
          onSubmit={handleSubmit}
          className="rounded-lg border border-border bg-card px-6 py-7 shadow-sm"
        >
          <h1 className="text-lg font-semibold text-foreground">Sign in</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Track where every application stands.
          </p>

          <div className="mt-6 space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="username" className="text-xs text-muted-foreground">
                Email
              </Label>
              <Input
                id="username"
                type="email"
                autoComplete="username"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="password" className="text-xs text-muted-foreground">
                Password
              </Label>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
          </div>

          {error && (
            <p className="mt-4 font-mono text-xs text-destructive" role="alert">
              {error}
            </p>
          )}

          <Button
            type="submit"
            disabled={status === "authenticating"}
            className="mt-6 w-full"
          >
            {status === "authenticating" ? "Authenticating…" : "Sign in"}
          </Button>

          <p className="mt-4 text-center text-xs text-muted-foreground">
            Don&apos;t have an account?{" "}
            <Link href="/signup" className="underline underline-offset-2 hover:text-foreground">
              Sign up
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}
