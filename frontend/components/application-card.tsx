import Link from "next/link";
import { StageBadge } from "@/components/stage-badge";
import { scoreColor } from "@/lib/jd-score";
import type { Application } from "@/lib/types";

// Mobile equivalent of a table row: minimal on purpose — company, role,
// stage. Tap through to the detail page for anything else (edit, notes,
// delete, stage change) rather than squeezing every column into a card.
export function ApplicationCard({ application }: { application: Application }) {
  return (
    <Link
      href={`/applications/${application.id}`}
      className="flex items-center justify-between gap-3 rounded-[3px] border border-border bg-card px-4 py-3 active:bg-muted/50"
    >
      <div className="min-w-0">
        <p className="truncate font-medium">{application.company}</p>
        <p className="truncate text-sm text-muted-foreground">{application.role_title}</p>
      </div>
      <div className="flex items-center gap-2">
        {application.match_score !== null && (
          <span
            className="font-mono text-xs tabular-nums"
            style={{ color: scoreColor(application.match_score) }}
          >
            {application.match_score}
          </span>
        )}
        <StageBadge stage={application.stage} />
      </div>
    </Link>
  );
}
