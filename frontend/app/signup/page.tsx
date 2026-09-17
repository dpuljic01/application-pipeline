"use client";

import { useState } from "react";
import type { FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { signUp, confirmSignUp, resendSignUpCode } from "@/lib/auth";
import { MagneticDots } from "@/components/magnetic-dots";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function SignUpPage() {
  const router = useRouter();
  const [step, setStep] = useState<"register" | "confirm">("register");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  async function handleRegister(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      await signUp(email, password);
      setStep("confirm");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign up failed");
    } finally {
      setPending(false);
    }
  }

  async function handleConfirm(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      await confirmSignUp(email, code);
      router.push("/login");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not confirm your account");
    } finally {
      setPending(false);
    }
  }

  async function handleResend() {
    setError(null);
    setNotice(null);
    try {
      await resendSignUpCode(email);
      setNotice("Code resent — check your email.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not resend the code");
    }
  }

  return (
    <div className="relative flex min-h-screen flex-1 items-center justify-center overflow-hidden bg-background px-4">
      <MagneticDots />
      <div className="relative z-10 w-full max-w-sm">
        <div className="mb-8 text-center">
          <p className="font-mono text-base font-medium tracking-[0.15em] text-foreground uppercase">
            JobDossier
          </p>
          <div className="mx-auto mt-3 h-px w-10 bg-border" />
        </div>

        <div className="rounded-lg border border-border bg-card px-6 py-7 shadow-sm">
          {step === "register" ? (
            <form onSubmit={handleRegister}>
              <h1 className="text-lg font-semibold text-foreground">Create an account</h1>
              <p className="mt-1 text-sm text-muted-foreground">
                Track your own job applications — free to try.
              </p>

              <div className="mt-6 space-y-4">
                <div className="space-y-1.5">
                  <Label htmlFor="email" className="text-xs text-muted-foreground">
                    Email
                  </Label>
                  <Input
                    id="email"
                    type="email"
                    autoComplete="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="password" className="text-xs text-muted-foreground">
                    Password
                  </Label>
                  <Input
                    id="password"
                    type="password"
                    autoComplete="new-password"
                    required
                    minLength={8}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                  />
                  <p className="text-xs text-muted-foreground">
                    At least 8 characters, with an uppercase letter, a lowercase letter, a
                    number, and a symbol.
                  </p>
                </div>
              </div>

              {error && (
                <p className="mt-4 font-mono text-xs text-destructive" role="alert">
                  {error}
                </p>
              )}

              <Button type="submit" disabled={pending} className="mt-6 w-full">
                {pending ? "Creating account…" : "Create account"}
              </Button>

              <p className="mt-4 text-center text-xs text-muted-foreground">
                Already have an account?{" "}
                <Link href="/login" className="underline underline-offset-2 hover:text-foreground">
                  Sign in
                </Link>
              </p>
            </form>
          ) : (
            <form onSubmit={handleConfirm}>
              <h1 className="text-lg font-semibold text-foreground">Check your email</h1>
              <p className="mt-1 text-sm text-muted-foreground">
                Enter the verification code we sent to {email}.
              </p>

              <div className="mt-6 space-y-1.5">
                <Label htmlFor="code" className="text-xs text-muted-foreground">
                  Verification code
                </Label>
                <Input
                  id="code"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  required
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                />
              </div>

              {error && (
                <p className="mt-4 font-mono text-xs text-destructive" role="alert">
                  {error}
                </p>
              )}
              {notice && (
                <p className="mt-4 text-xs text-muted-foreground" role="status">
                  {notice}
                </p>
              )}

              <Button type="submit" disabled={pending} className="mt-6 w-full">
                {pending ? "Confirming…" : "Confirm account"}
              </Button>

              <button
                type="button"
                onClick={handleResend}
                className="mt-4 w-full text-center text-xs text-muted-foreground underline underline-offset-2 hover:text-foreground"
              >
                Resend code
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
