"use client";

import { useState } from "react";
import type { FormEvent } from "react";
import { ChevronDown } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ALLOWED_TRANSITIONS } from "@/lib/types";
import type { Application, ApplicationStage } from "@/lib/types";
import { changeApplicationStage, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { fromDateInputValue, toDateInputValue, todayDateInputValue } from "@/lib/stage-date";

export function StageChangeMenu({
  application,
  onChanged,
  onUnauthorized,
}: {
  application: Application;
  onChanged: (updated: Application) => void;
  onUnauthorized: () => void;
}) {
  const { idToken } = useAuth();
  const [pending, setPending] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  // Kept set to the last-selected stage even while the dialog is closing, so
  // the exit animation doesn't briefly render "Move to null".
  const [pendingStage, setPendingStage] = useState<ApplicationStage | null>(null);
  const [occurredDate, setOccurredDate] = useState(todayDateInputValue());
  const [error, setError] = useState<string | null>(null);
  const nextStages = ALLOWED_TRANSITIONS[application.stage];

  function handleSelect(stage: ApplicationStage) {
    setOccurredDate(todayDateInputValue());
    setError(null);
    setPendingStage(stage);
    setDialogOpen(true);
  }

  async function handleConfirm(event: FormEvent) {
    event.preventDefault();
    if (!idToken || !pendingStage) return;
    setPending(true);
    setError(null);
    try {
      const updated = await changeApplicationStage(idToken, application.id, {
        stage: pendingStage,
        occurred_at: fromDateInputValue(occurredDate, application.created_at),
      });
      onChanged(updated);
      setDialogOpen(false);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        onUnauthorized();
        return;
      }
      setError(err instanceof Error ? err.message : "Could not change stage");
    } finally {
      setPending(false);
    }
  }

  if (nextStages.length === 0) {
    return (
      <Button
        variant="outline"
        size="sm"
        disabled
        title="Terminal stage — no further transitions"
        className="h-7 text-xs"
      >
        Change stage
        <ChevronDown className="size-3" />
      </Button>
    );
  }

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger
          render={<Button variant="outline" size="sm" disabled={pending} className="h-7 text-xs" />}
        >
          Change stage
          <ChevronDown className="size-3" />
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          {nextStages.map((stage) => (
            <DropdownMenuItem key={stage} onClick={() => handleSelect(stage)}>
              <span className="font-mono text-xs">{stage}</span>
            </DropdownMenuItem>
          ))}
        </DropdownMenuContent>
      </DropdownMenu>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <form onSubmit={handleConfirm}>
            <DialogHeader>
              <DialogTitle>Move to {pendingStage}</DialogTitle>
              <DialogDescription>
                When did this actually happen? Defaults to today — change it if
                you&apos;re logging this late.
              </DialogDescription>
            </DialogHeader>

            <div className="mt-4 space-y-1.5">
              <Label htmlFor="stage_occurred_date" className="text-xs text-muted-foreground">
                Date
              </Label>
              <Input
                id="stage_occurred_date"
                type="date"
                required
                min={toDateInputValue(application.created_at)}
                max={todayDateInputValue()}
                value={occurredDate}
                onChange={(e) => setOccurredDate(e.target.value)}
              />
            </div>

            {error && (
              <p className="mt-3 font-mono text-xs text-destructive" role="alert">
                {error}
              </p>
            )}

            <DialogFooter className="mt-6">
              <Button type="submit" disabled={pending}>
                {pending ? "Saving…" : "Confirm"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </>
  );
}
