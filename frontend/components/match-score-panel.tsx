"use client";

import { useState } from "react";
import { scoreApplication, ApiError } from "@/lib/api";
import type { Application } from "@/lib/types";
import { PostingScoreGauge } from "@/components/posting-score-gauge";
import { Button } from "@/components/ui/button";

export function MatchScorePanel({
  application,
  idToken,
  onScored,
  onUnauthorized,
}: {
  application: Application;
  idToken: string;
  onScored: (application: Application) => void;
  onUnauthorized: () => void;
}) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleScore() {
    setLoading(true);
    setError(null);
    try {
      const updated = await scoreApplication(idToken, application.id);
      onScored(updated);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        onUnauthorized();
        return;
      }
      setError(err instanceof Error ? err.message : "Scoring failed");
    } finally {
      setLoading(false);
    }
  }

  if (!application.parsed_jd) {
    return (
      <div className="rounded-[3px] border border-dashed border-border px-4 py-4 text-center">
        <p className="text-xs text-muted-foreground">
          Parse the job description above before scoring the match.
        </p>
      </div>
    );
  }

  const details = application.match_details;

  return (
    <div className="rounded-[3px] border border-border bg-card px-4 py-4">
      <div className="mb-4 flex items-center justify-between">
        <p className="text-sm font-medium text-foreground">Job match</p>
        <Button size="sm" variant="outline" className="h-7 text-xs" onClick={handleScore} disabled={loading}>
          {loading ? "Scoring…" : application.match_score === null ? "Score match" : "Re-score"}
        </Button>
      </div>

      {error && (
        <p className="mb-3 font-mono text-xs text-destructive" role="alert">
          {error}
        </p>
      )}

      {application.match_score !== null && details && (
        <div className="space-y-5">
          <PostingScoreGauge
            score={application.match_score}
            label="Job match"
            caption="Based on your profile: skills, seniority, salary & remote policy"
          />

          <p className="text-sm text-foreground">{details.insights.fit_narrative}</p>

          {details.insights.key_strengths.length > 0 && (
            <div>
              <p className="mb-1.5 text-xs font-medium text-muted-foreground">
                Key strengths
              </p>
              <ul className="space-y-1">
                {details.insights.key_strengths.map((item) => (
                  <li key={item} className="text-sm text-foreground">
                    · {item}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {details.insights.gaps.length > 0 && (
            <div>
              <p className="mb-1.5 text-xs font-medium text-muted-foreground">Gaps</p>
              <ul className="space-y-1">
                {details.insights.gaps.map((item) => (
                  <li key={item} className="text-sm text-muted-foreground">
                    · {item}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {details.insights.talking_points.length > 0 && (
            <div>
              <p className="mb-1.5 text-xs font-medium text-muted-foreground">
                Cover-letter talking points
              </p>
              <ul className="space-y-1">
                {details.insights.talking_points.map((item) => (
                  <li key={item} className="text-sm text-foreground">
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
