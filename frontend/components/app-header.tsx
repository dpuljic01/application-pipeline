import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";

// Shared across the dashboard, application detail, and profile pages so
// Profile/Sign out are always reachable — previously only the dashboard
// header had them, leaving no way to sign out from the other two.
export function AppHeader({
  email,
  onSignOut,
  back,
}: {
  email?: string | null;
  onSignOut: () => void;
  back?: { href: string; label: string };
}) {
  return (
    <header className="border-b border-border">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
        {back ? (
          <Link
            href={back.href}
            className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="size-3.5" />
            {back.label}
          </Link>
        ) : (
          <div>
            <p className="font-mono text-base font-medium tracking-[0.15em] text-foreground uppercase">
              Job Dossier
            </p>
            {email && <p className="mt-0.5 text-xs text-muted-foreground">{email}</p>}
          </div>
        )}

        <div className="flex items-center gap-2">
          <Link href="/profile">
            <Button variant="ghost" size="sm">
              Profile
            </Button>
          </Link>
          <div className="h-4 w-px bg-border" aria-hidden />
          <Button variant="ghost" size="sm" onClick={onSignOut}>
            Sign out
          </Button>
        </div>
      </div>
    </header>
  );
}
