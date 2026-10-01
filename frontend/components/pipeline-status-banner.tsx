import { AlertTriangle, Loader2 } from "lucide-react";
import { isPipelineRunning } from "@/lib/pipeline";
import type { Application } from "@/lib/types";

export function PipelineStatusBanner({ application }: { application: Application }) {
  if (isPipelineRunning(application)) {
    return (
      <div className="flex items-center gap-2 rounded-[3px] border border-border bg-card px-4 py-3 text-xs text-muted-foreground">
        <Loader2 className="size-3.5 animate-spin" />
        Analyzing the posting and scoring it against your profile…
      </div>
    );
  }

  // Once a match score exists (e.g. the user retried manually), an earlier
  // failure is no longer worth shouting about.
  if (application.pipeline_status === "FAILED" && application.match_score === null) {
    return (
      <div
        role="alert"
        className="flex items-start gap-2 rounded-[3px] border border-destructive/40 bg-destructive/10 px-4 py-3 text-xs text-destructive"
      >
        <AlertTriangle className="mt-px size-3.5 shrink-0" />
        <span>
          Automatic analysis stopped: {application.pipeline_error ?? "unknown error"}.
          You can retry from the panels below.
        </span>
      </div>
    );
  }

  return null;
}
