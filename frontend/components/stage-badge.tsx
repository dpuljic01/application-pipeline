import { Ghost, Undo2, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ApplicationStage } from "@/lib/types";

// Same colors as the Pipeline chart (components/stage-breakdown.tsx):
// Applied's blue, Interview as a subtle indigo shift off it, a distinct
// orange for Offer (the "getting real" moment), and the existing win-green
// for Accepted. Not --primary's amber anywhere here.
const STAGE_STYLES: Record<ApplicationStage, string> = {
  SAVED: "border border-border bg-transparent text-muted-foreground",
  APPLIED:
    "border border-[var(--stage-progress)]/30 bg-[var(--stage-progress)]/10 text-[var(--stage-progress)]",
  INTERVIEW:
    "border border-[var(--stage-interview)]/50 bg-[var(--stage-interview)]/20 text-[var(--stage-interview)]",
  OFFER: "border border-[var(--stage-offer)] bg-[var(--stage-offer)]/85 text-[#14110a]",
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
        "inline-flex items-center gap-1 rounded-[3px] px-2 py-0.5 font-mono text-[11px] tracking-wide uppercase",
        STAGE_STYLES[stage],
      )}
    >
      {Icon && <Icon className="size-3" />}
      {stage}
    </span>
  );
}
