import { Ghost, Undo2, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ApplicationStage } from "@/lib/types";

// Visual weight increases as an application moves through the pipeline —
// the badge itself communicates "how far along is this one" at a glance.
// Terminal states (win or exit) get their own distinct treatment.
const STAGE_STYLES: Record<ApplicationStage, string> = {
  SAVED: "border border-border bg-transparent text-muted-foreground",
  APPLIED: "border border-primary/30 bg-primary/10 text-primary",
  INTERVIEW: "border border-primary/50 bg-primary/20 text-primary",
  OFFER: "border border-primary bg-primary/85 text-primary-foreground",
  ACCEPTED: "border border-transparent bg-[var(--stage-win)] text-[var(--stage-win-foreground)]",
  REJECTED: "border border-transparent bg-[var(--stage-exit)] text-[var(--stage-exit-foreground)]",
  WITHDRAWN: "border border-transparent bg-[var(--stage-exit)] text-[var(--stage-exit-foreground)]",
  GHOSTED: "border border-transparent bg-[var(--stage-exit)] text-[var(--stage-exit-foreground)]",
};

const EXIT_ICON: Partial<Record<ApplicationStage, typeof XCircle>> = {
  REJECTED: XCircle,
  WITHDRAWN: Undo2,
  GHOSTED: Ghost,
};

export function StageBadge({ stage }: { stage: ApplicationStage }) {
  const Icon = EXIT_ICON[stage];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 font-mono text-[11px] tracking-wide uppercase",
        STAGE_STYLES[stage],
      )}
    >
      {Icon && <Icon className="size-3" />}
      {stage}
    </span>
  );
}
