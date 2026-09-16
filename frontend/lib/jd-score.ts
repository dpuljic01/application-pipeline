import type { ParsedJobDescription } from "@/lib/types";

// Not a job-fit/match score (that needs a candidate profile, which this app
// doesn't model yet) — this measures how transparent/complete the posting
// itself is: fewer red flags and missing details score higher.
export function postingQualityScore(parsed: ParsedJobDescription): number {
  let score = 100;
  score -= parsed.red_flags.length * 15;
  score -= parsed.missing_info.length * 8;
  if (parsed.salary_confidence === "estimated") score -= 5;
  if (parsed.salary_confidence === "unknown") score -= 10;
  return Math.max(0, Math.min(100, score));
}

export function postingScoreColor(score: number): string {
  if (score >= 70) return "var(--stage-win)";
  if (score >= 40) return "var(--primary)";
  return "var(--destructive)";
}
