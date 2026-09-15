"use client";

import { useState } from "react";
import { Trash2 } from "lucide-react";
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
import { deleteApplication, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Application } from "@/lib/types";

export function DeleteApplicationDialog({
  application,
  onDeleted,
  onUnauthorized,
}: {
  application: Application;
  onDeleted: (applicationId: string) => void;
  onUnauthorized: () => void;
}) {
  const { idToken } = useAuth();
  const [open, setOpen] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function handleOpenChange(next: boolean) {
    if (next) setError(null);
    setOpen(next);
  }

  async function handleConfirm() {
    if (!idToken) return;
    setPending(true);
    setError(null);
    try {
      await deleteApplication(idToken, application.id);
      onDeleted(application.id);
      setOpen(false);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        onUnauthorized();
        return;
      }
      setError(err instanceof Error ? err.message : "Could not delete application");
    } finally {
      setPending(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger
        render={<Button variant="destructive" size="sm" className="h-7 text-xs" />}
      >
        <Trash2 className="size-3" />
        Delete
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Delete application</DialogTitle>
          <DialogDescription>
            Remove <span className="font-medium text-foreground">{application.role_title}</span>{" "}
            at <span className="font-medium text-foreground">{application.company}</span>?
            This also deletes its activity history and can&apos;t be undone.
          </DialogDescription>
        </DialogHeader>

        {error && (
          <p className="mt-3 font-mono text-xs text-destructive" role="alert">
            {error}
          </p>
        )}

        <DialogFooter className="mt-6">
          <Button variant="outline" size="sm" onClick={() => setOpen(false)} disabled={pending}>
            Cancel
          </Button>
          <Button variant="destructive" size="sm" onClick={handleConfirm} disabled={pending}>
            {pending ? "Deleting…" : "Delete"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
