import type { Application, ApplicationStage } from "@/lib/types";

// Only stages where "no response" genuinely calls for a follow-up. SAVED
// hasn't been sent anywhere yet, OFFER is the candidate's own decision to
// make, and terminal stages are done.
const STALE_THRESHOLD_DAYS: Partial<Record<ApplicationStage, number>> = {
  APPLIED: 14,
  INTERVIEW: 7,
};

export function daysSince(iso: string): number {
  const ms = Date.now() - new Date(iso).getTime();
  return Math.floor(ms / (1000 * 60 * 60 * 24));
}

export function needsFollowUp(application: Application): boolean {
  const threshold = STALE_THRESHOLD_DAYS[application.stage];
  if (threshold === undefined || application.stage_changed_at === null) {
    return false;
  }
  return daysSince(application.stage_changed_at) >= threshold;
}
