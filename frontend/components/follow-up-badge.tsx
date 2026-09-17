import { Clock } from "lucide-react";

// Amber (--primary) is deliberately unused by StageBadge's own stage
// colors (see its comment) - free for exactly this kind of "needs
// attention" signal. Icon-only, not a text pill: next to StageBadge in
// both the desktop table (9 columns already) and the mobile card
// (minimal by design), a labeled badge was too wide/obtrusive. The full
// "consider a follow-up" framing lives on the detail page instead.
export function FollowUpBadge() {
  return (
    <span
      title="Needs follow-up"
      className="inline-flex items-center justify-center rounded-[3px] border border-[var(--primary)]/40 bg-[var(--primary)]/10 p-1 text-[var(--primary)]"
    >
      <Clock className="size-3" />
    </span>
  );
}
