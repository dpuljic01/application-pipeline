import { Loader2 } from "lucide-react";

// Shown while AuthProvider is trading the refresh cookie for an ID token.
// That request hits the Render free-tier backend, which can take up to
// ~50s to wake from a cold start — without this, pages that gate on
// `isRestoring` rendered nothing at all for that whole stretch.
export function LoadingScreen() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-3 bg-background">
      <Loader2 className="size-5 animate-spin text-muted-foreground" />
      <p className="font-mono text-xs text-muted-foreground">Loading…</p>
    </div>
  );
}
