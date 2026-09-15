import {
  ArrowRightLeft,
  Ghost,
  MessageSquare,
  PhoneCall,
  Send,
  Sparkles,
  ThumbsDown,
  Trophy,
  Undo2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { Activity, ActivityType } from "@/lib/types";

const ACTIVITY_ICON: Record<ActivityType, typeof MessageSquare> = {
  NOTE: MessageSquare,
  OUTREACH: Send,
  FOLLOW_UP: Undo2,
  INTERVIEW: PhoneCall,
  OFFER: Sparkles,
  ACCEPTED: Trophy,
  REJECTION: ThumbsDown,
  GHOSTED: Ghost,
  STAGE_CHANGE: ArrowRightLeft,
};

const ACTIVITY_STYLES: Record<ActivityType, string> = {
  NOTE: "text-muted-foreground",
  OUTREACH: "text-primary",
  FOLLOW_UP: "text-primary",
  INTERVIEW: "text-primary",
  OFFER: "text-primary",
  ACCEPTED: "text-[var(--stage-win)]",
  REJECTION: "text-[var(--stage-exit)]",
  GHOSTED: "text-[var(--stage-exit)]",
  STAGE_CHANGE: "text-muted-foreground",
};

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function ActivityTimeline({ activities }: { activities: Activity[] }) {
  if (activities.length === 0) {
    return (
      <div className="rounded-[3px] border border-dashed border-border py-10 text-center">
        <p className="text-sm text-muted-foreground">No notes yet.</p>
        <p className="mt-1 text-xs text-muted-foreground">
          Add one after your next interview or call.
        </p>
      </div>
    );
  }

  return (
    <ol className="space-y-4">
      {activities.map((activity) => {
        const Icon = ACTIVITY_ICON[activity.activity_type];
        return (
          <li key={activity.id} className="flex gap-3">
            <div
              className={cn(
                "mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-full border border-border bg-card",
                ACTIVITY_STYLES[activity.activity_type],
              )}
            >
              <Icon className="size-3.5" />
            </div>
            <div className="flex-1 pb-1">
              <div className="flex items-center gap-2">
                <span className="font-mono text-[11px] tracking-wide text-muted-foreground uppercase">
                  {activity.activity_type.replace("_", " ")}
                </span>
                <span className="text-xs text-muted-foreground">
                  {formatDateTime(activity.occurred_at)}
                </span>
              </div>
              {activity.note && (
                <p className="mt-1 text-sm whitespace-pre-wrap text-foreground">
                  {activity.note}
                </p>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
