import { Clock } from "lucide-react";

// Amber (--primary) is deliberately unused by StageBadge's own stage
// colors (see its comment) - free for exactly this kind of "needs
// attention" signal.
export function FollowUpBadge() {
  return (
    <span className="inline-flex items-center gap-1 rounded-[3px] border border-[var(--primary)]/40 bg-[var(--primary)]/10 px-2 py-0.5 font-mono text-[11px] tracking-wide text-[var(--primary)] uppercase">
      <Clock className="size-3" />
      Follow up
    </span>
  );
}
