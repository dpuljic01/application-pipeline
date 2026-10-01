import { useEffect, useRef } from "react";
import type { Application } from "@/lib/types";

// The backend runs the pipeline as an in-process background task, so a
// server restart mid-run leaves the row PENDING forever. Past this age,
// stop treating it as running (and stop polling) - the panels' manual
// analyze/score buttons are still there.
const STALE_AFTER_MS = 5 * 60 * 1000;
const POLL_INTERVAL_MS = 3000;

export function isPipelineRunning(application: Application): boolean {
  return (
    application.pipeline_status === "PENDING" &&
    Date.now() - new Date(application.created_at).getTime() < STALE_AFTER_MS
  );
}

// Calls `poll` every few seconds while `active`. Each poll is expected to
// update state, which re-renders and recomputes `active` - so polling stops
// on its own once the pipeline finishes or goes stale.
export function usePolling(active: boolean, poll: () => Promise<void>) {
  const pollRef = useRef(poll);
  useEffect(() => {
    pollRef.current = poll;
  });

  useEffect(() => {
    if (!active) return;
    const id = setInterval(() => {
      pollRef.current().catch(() => {
        // Transient poll failures are ignored; the next tick retries.
      });
    }, POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [active]);
}
