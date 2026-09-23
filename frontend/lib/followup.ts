import type { Application, ApplicationStage } from "@/lib/types";

// Only stages where "no response" genuinely calls for a follow-up. SAVED
// hasn't been sent anywhere yet, OFFER is the candidate's own decision to
// make, and terminal stages are done.
const STALE_THRESHOLD_DAYS: Partial<Record<ApplicationStage, number>> = {
  APPLIED: 10,
  INTERVIEW: 7,
};

export function daysSince(iso: string): number {
  const ms = Date.now() - new Date(iso).getTime();
  return Math.floor(ms / (1000 * 60 * 60 * 24));
}

export function needsFollowUp(application: Application): boolean {
  const threshold = STALE_THRESHOLD_DAYS[application.stage];
  // last_activity_at updates on ANY logged activity (a note, a stage
  // change, etc.), not just an outbound follow-up - so it's already the
  // right "time since anything happened" signal, and always >=
  // stage_changed_at since a stage transition itself logs an activity.
  const reference = application.last_activity_at ?? application.stage_changed_at;
  if (threshold === undefined || reference === null) {
    return false;
  }
  return daysSince(reference) >= threshold;
}
