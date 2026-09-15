import type { Application, ApplicationStage } from "@/lib/types";

// Interview is a subtle indigo shift off Applied's blue — same family
// (both "still pending"), just enough violet to read as distinct. See
// globals.css for why it's a gentle tint rather than a full 4th color.
const FUNNEL: { stage: ApplicationStage; label: string; color: string }[] = [
  { stage: "SAVED", label: "Saved", color: "var(--stage-neutral)" },
  { stage: "APPLIED", label: "Applied", color: "var(--stage-progress)" },
  { stage: "INTERVIEW", label: "Interview", color: "var(--stage-interview)" },
  { stage: "OFFER", label: "Offer", color: "var(--stage-offer)" },
  { stage: "ACCEPTED", label: "Accepted", color: "var(--stage-win)" },
];

export function StageBreakdown({ applications }: { applications: Application[] }) {
  if (applications.length === 0) return null;

  const rows = FUNNEL.map(({ stage, label, color }) => ({
    label,
    color,
    count: applications.filter((app) => app.stage === stage).length,
  }));
  const max = Math.max(1, ...rows.map((row) => row.count));

  const rejected = applications.filter((app) => app.stage === "REJECTED").length;
  const withdrawn = applications.filter((app) => app.stage === "WITHDRAWN").length;
  const ghosted = applications.filter((app) => app.stage === "GHOSTED").length;
  const exited = rejected + withdrawn + ghosted;
  const exitParts = [
    rejected > 0 && `${rejected} rejected`,
    withdrawn > 0 && `${withdrawn} withdrawn`,
    ghosted > 0 && `${ghosted} ghosted`,
  ].filter((part): part is string => Boolean(part));

  return (
    <div className="rounded-[3px] border border-border bg-card px-4 py-4">
      <p className="mb-4 text-sm font-medium text-foreground">Pipeline</p>
      <div className="space-y-3">
        {rows.map(({ label, color, count }) => (
          <div key={label} className="flex items-center gap-3">
            <span className="size-2.5 shrink-0 rounded-full" style={{ backgroundColor: color }} />
            <span className="w-20 shrink-0 text-sm text-muted-foreground">{label}</span>
            <div className="h-3.5 flex-1">
              <div
                className="h-3.5 rounded-full"
                style={{
                  width: count > 0 ? `${(count / max) * 100}%` : 0,
                  backgroundColor: color,
                }}
              />
            </div>
            <span className="w-5 shrink-0 text-right text-sm text-foreground tabular-nums">
              {count}
            </span>
          </div>
        ))}
      </div>

      {exited > 0 && (
        <p className="mt-4 border-t border-border pt-3 text-sm text-muted-foreground">
          {exited} {exited === 1 ? "application" : "applications"} exited the pipeline
          {exitParts.length > 0 && ` (${exitParts.join(", ")})`}
        </p>
      )}
    </div>
  );
}
