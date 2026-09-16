"use client";

import { useState } from "react";
import { AlertTriangle } from "lucide-react";
import { parseJd, ApiError } from "@/lib/api";
import type { ParsedJobDescription } from "@/lib/types";
import { postingQualityScore } from "@/lib/jd-score";
import { PostingScoreGauge } from "@/components/posting-score-gauge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

function Tag({ children }: { children: React.ReactNode }) {
  return (
    <span className="rounded-[3px] border border-border bg-muted px-1.5 py-0.5 font-mono text-[11px] text-foreground">
      {children}
    </span>
  );
}

export function JdParsePanel({
  applicationId,
  idToken,
  parsedJd,
  onParsed,
  onUnauthorized,
}: {
  applicationId: string;
  idToken: string;
  parsedJd: ParsedJobDescription | null;
  onParsed: (parsed: ParsedJobDescription) => void;
  onUnauthorized: () => void;
}) {
  const [jdText, setJdText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(!parsedJd);

  async function handleAnalyze() {
    if (!jdText.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const result = await parseJd(idToken, applicationId, jdText);
      onParsed(result);
      setExpanded(false);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        onUnauthorized();
        return;
      }
      setError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="rounded-[3px] border border-border bg-card px-4 py-4">
      <div className="mb-4 flex items-center justify-between">
        <p className="text-sm font-medium text-foreground">JD analysis</p>
        {parsedJd && (
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            className="text-xs text-muted-foreground underline decoration-border underline-offset-2 hover:text-foreground hover:decoration-foreground"
          >
            {expanded ? "Hide" : "Re-analyze"}
          </button>
        )}
      </div>

      {expanded && (
        <div className="mb-4 space-y-2">
          <Textarea
            value={jdText}
            onChange={(e) => setJdText(e.target.value)}
            placeholder="Paste the job description here…"
            rows={6}
          />
          <div className="flex items-center gap-3">
            <Button size="sm" onClick={handleAnalyze} disabled={loading || !jdText.trim()}>
              {loading ? "Analyzing…" : "Analyze"}
            </Button>
            {error && <p className="text-xs text-destructive">{error}</p>}
          </div>
        </div>
      )}

      {parsedJd && !expanded && (
        <div className="space-y-5">
          <PostingScoreGauge score={postingQualityScore(parsedJd)} label="Posting clarity" />

          <p className="text-sm text-foreground">{parsedJd.summary}</p>

          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-xs font-medium text-muted-foreground">Seniority</p>
              <p className="mt-0.5 text-foreground capitalize">
                {parsedJd.seniority_assessed}
                {parsedJd.seniority_claimed &&
                  parsedJd.seniority_claimed.toLowerCase() !==
                    parsedJd.seniority_assessed && (
                    <span className="text-muted-foreground">
                      {" "}
                      (title says &ldquo;{parsedJd.seniority_claimed}&rdquo;)
                    </span>
                  )}
              </p>
            </div>
            <div>
              <p className="text-xs font-medium text-muted-foreground">Salary</p>
              <p className="mt-0.5 text-foreground">
                {parsedJd.salary_range ?? "Not stated"}
                {parsedJd.salary_confidence !== "stated" && (
                  <span className="text-muted-foreground">
                    {" "}
                    ({parsedJd.salary_confidence})
                  </span>
                )}
              </p>
            </div>
          </div>

          {parsedJd.tech_stack.length > 0 && (
            <div>
              <p className="mb-1.5 text-xs font-medium text-muted-foreground">Tech stack</p>
              <div className="flex flex-wrap gap-1.5">
                {parsedJd.tech_stack.map((t) => (
                  <Tag key={t}>{t}</Tag>
                ))}
              </div>
            </div>
          )}

          {parsedJd.red_flags.length > 0 && (
            <div>
              <p className="mb-1.5 flex items-center gap-1.5 text-xs font-medium text-destructive">
                <AlertTriangle className="size-3.5" />
                Red flags
              </p>
              <ul className="space-y-1">
                {parsedJd.red_flags.map((flag) => (
                  <li key={flag} className="text-sm text-foreground">
                    · {flag}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {parsedJd.missing_info.length > 0 && (
            <div>
              <p className="mb-1.5 text-xs font-medium text-muted-foreground">Missing info</p>
              <ul className="space-y-1">
                {parsedJd.missing_info.map((item) => (
                  <li key={item} className="text-sm text-muted-foreground">
                    · {item}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
