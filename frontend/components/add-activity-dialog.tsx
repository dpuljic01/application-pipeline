"use client";

import { useState } from "react";
import type { FormEvent } from "react";
import { Plus } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { createActivity, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { MANUAL_ACTIVITY_TYPES } from "@/lib/types";
import type { Activity, ActivityType } from "@/lib/types";

// <input type="date"> works in YYYY-MM-DD; noon avoids a date rolling back a
// day across timezones when converted to the ISO datetime the API expects.
function todayDateInputValue(): string {
  return new Date().toISOString().slice(0, 10);
}

export function AddActivityDialog({
  applicationId,
  onAdded,
  onUnauthorized,
}: {
  applicationId: string;
  onAdded: (activity: Activity) => void;
  onUnauthorized: () => void;
}) {
  const { idToken } = useAuth();
  const [open, setOpen] = useState(false);
  const [activityType, setActivityType] = useState<ActivityType>("NOTE");
  const [note, setNote] = useState("");
  const [occurredAt, setOccurredAt] = useState(todayDateInputValue());
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function handleOpenChange(next: boolean) {
    if (next) {
      setActivityType("NOTE");
      setNote("");
      setOccurredAt(todayDateInputValue());
      setError(null);
    }
    setOpen(next);
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!idToken) return;
    setPending(true);
    setError(null);
    try {
      const activity = await createActivity(idToken, applicationId, {
        activity_type: activityType,
        note: note || null,
        occurred_at: `${occurredAt}T12:00:00Z`,
      });
      onAdded(activity);
      setOpen(false);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        onUnauthorized();
        return;
      }
      setError(err instanceof Error ? err.message : "Could not add note");
    } finally {
      setPending(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger render={<Button variant="outline" size="sm" className="h-7 text-xs" />}>
        <Plus className="size-3" />
        Add note
      </DialogTrigger>
      <DialogContent>
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>Add note</DialogTitle>
            <DialogDescription>
              Log an interview, a follow-up, or anything else worth remembering —
              this becomes part of the application&apos;s timeline.
            </DialogDescription>
          </DialogHeader>

          <div className="mt-4 space-y-3">
            <div className="space-y-1.5">
              <Label htmlFor="activity_type" className="text-xs text-muted-foreground">
                Type
              </Label>
              <Select
                value={activityType}
                onValueChange={(value) => setActivityType(value as ActivityType)}
              >
                <SelectTrigger id="activity_type" className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {MANUAL_ACTIVITY_TYPES.map((type) => (
                    <SelectItem key={type} value={type}>
                      {type}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="activity_note" className="text-xs text-muted-foreground">
                Note
              </Label>
              <Textarea
                id="activity_note"
                rows={4}
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="How did it go? Who did you speak with? Anything to follow up on?"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="activity_occurred_at" className="text-xs text-muted-foreground">
                Date
              </Label>
              <Input
                id="activity_occurred_at"
                type="date"
                value={occurredAt}
                onChange={(e) => setOccurredAt(e.target.value)}
              />
            </div>
          </div>

          {error && (
            <p className="mt-3 font-mono text-xs text-destructive" role="alert">
              {error}
            </p>
          )}

          <DialogFooter className="mt-6">
            <Button type="submit" disabled={pending}>
              {pending ? "Saving…" : "Add note"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
