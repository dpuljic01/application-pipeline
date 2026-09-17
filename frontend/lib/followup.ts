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
  // Logging a follow-up activity resets the clock: if it happened more
  // recently than the stage change, count staleness from there instead -
  // otherwise the badge never clears once you've actually followed up.
  const reference =
    application.last_followup_at &&
    new Date(application.last_followup_at) > new Date(application.stage_changed_at)
      ? application.last_followup_at
      : application.stage_changed_at;
  return daysSince(reference) >= threshold;
}
