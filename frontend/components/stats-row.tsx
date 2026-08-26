import type { Application } from "@/lib/types";

function Stat({
  label,
  value,
  className,
}: {
  label: string;
  value: number;
  className?: string;
}) {
  return (
    <div className="rounded-lg border border-border bg-card px-4 py-3">
      <p className="font-mono text-[11px] tracking-wider text-muted-foreground uppercase">
        {label}
      </p>
      <p className={`mt-1 text-2xl font-semibold tabular-nums ${className ?? "text-foreground"}`}>
        {value}
      </p>
    </div>
  );
}

export function StatsRow({ applications }: { applications: Application[] }) {
  const interviewing = applications.filter((app) => app.stage === "INTERVIEW").length;
  const offers = applications.filter(
    (app) => app.stage === "OFFER" || app.stage === "ACCEPTED",
  ).length;
  const rejectedOrGhosted = applications.filter(
    (app) => app.stage === "REJECTED" || app.stage === "GHOSTED",
  ).length;

  return (
    <div className="mb-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
      <Stat label="Total" value={applications.length} />
      <Stat label="Interviewing" value={interviewing} className="text-primary" />
      <Stat label="Offers" value={offers} className="text-[var(--stage-win)]" />
      <Stat
        label="Rejected / Ghosted"
        value={rejectedOrGhosted}
        className="text-muted-foreground"
      />
    </div>
  );
}
