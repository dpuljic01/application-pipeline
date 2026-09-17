"use client";

import { useState } from "react";
import { Check, Clock, Copy } from "lucide-react";
import { generateFollowUp, ApiError } from "@/lib/api";
import { daysSince, needsFollowUp } from "@/lib/followup";
import type { Application } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

export function FollowUpPanel({
  application,
  idToken,
  onGenerated,
  onUnauthorized,
}: {
  application: Application;
  idToken: string;
  onGenerated: (application: Application) => void;
  onUnauthorized: () => void;
}) {
  const [context, setContext] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const stale = needsFollowUp(application);

  async function handleGenerate() {
    setLoading(true);
    setError(null);
    setCopied(false);
    try {
      const updated = await generateFollowUp(
        idToken,
        application.id,
        context.trim() || undefined,
      );
      onGenerated(updated);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        onUnauthorized();
        return;
      }
      setError(err instanceof Error ? err.message : "Could not generate a follow-up");
    } finally {
      setLoading(false);
    }
  }

  async function handleCopy() {
    if (!application.generated_followup) return;
    const { subject, body } = application.generated_followup;
    await navigator.clipboard.writeText(`Subject: ${subject}\n\n${body}`);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="rounded-[3px] border border-border bg-card px-4 py-4">
      <p className="mb-4 text-sm font-medium text-foreground">Follow-up email</p>

      {stale && application.stage_changed_at && (
        <div className="mb-4 flex items-center gap-1.5 rounded-[3px] border border-[var(--primary)]/40 bg-[var(--primary)]/10 px-3 py-2 text-xs text-[var(--primary)]">
          <Clock className="size-3.5" />
          {daysSince(application.stage_changed_at)} days at {application.stage} with no
          update. Consider a follow-up.
        </div>
      )}

      <div className="mb-4 space-y-2">
        <Textarea
          value={context}
          onChange={(e) => setContext(e.target.value)}
          placeholder="Optional context, e.g. mention an upcoming interview…"
          rows={2}
        />
        <div className="flex items-center gap-3">
          <Button size="sm" onClick={handleGenerate} disabled={loading}>
            {loading
              ? "Generating…"
              : application.generated_followup
                ? "Regenerate"
                : "Generate follow-up"}
          </Button>
          {error && <p className="text-xs text-destructive">{error}</p>}
        </div>
      </div>

      {application.generated_followup && (
        <div className="space-y-3 border-t border-border pt-4">
          <div>
            <p className="text-xs font-medium text-muted-foreground">Subject</p>
            <p className="mt-0.5 text-sm text-foreground">
              {application.generated_followup.subject}
            </p>
          </div>
          <div>
            <p className="text-xs font-medium text-muted-foreground">Body</p>
            <p className="mt-0.5 text-sm whitespace-pre-wrap text-foreground">
              {application.generated_followup.body}
            </p>
          </div>
          <Button size="sm" variant="outline" className="h-7 text-xs" onClick={handleCopy}>
            {copied ? <Check className="size-3" /> : <Copy className="size-3" />}
            {copied ? "Copied" : "Copy"}
          </Button>
        </div>
      )}
    </div>
  );
}
