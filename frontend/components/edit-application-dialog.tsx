"use client";

import { useState } from "react";
import type { FormEvent } from "react";
import { Pencil } from "lucide-react";
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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { updateApplication, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Application } from "@/lib/types";

export function EditApplicationDialog({
  application,
  onUpdated,
  onUnauthorized,
}: {
  application: Application;
  onUpdated: (application: Application) => void;
  onUnauthorized: () => void;
}) {
  const { idToken } = useAuth();
  const [open, setOpen] = useState(false);
  const [company, setCompany] = useState(application.company);
  const [roleTitle, setRoleTitle] = useState(application.role_title);
  const [jobUrl, setJobUrl] = useState(application.job_url ?? "");
  const [location, setLocation] = useState(application.location ?? "");
  const [salaryRange, setSalaryRange] = useState(application.salary_range ?? "");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function handleOpenChange(next: boolean) {
    if (next) {
      // Reset to current values each time the dialog opens
      setCompany(application.company);
      setRoleTitle(application.role_title);
      setJobUrl(application.job_url ?? "");
      setLocation(application.location ?? "");
      setSalaryRange(application.salary_range ?? "");
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
      const updated = await updateApplication(idToken, application.id, {
        company,
        role_title: roleTitle,
        job_url: jobUrl || null,
        location: location || null,
        salary_range: salaryRange || null,
      });
      onUpdated(updated);
      setOpen(false);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        onUnauthorized();
        return;
      }
      setError(err instanceof Error ? err.message : "Could not save changes");
    } finally {
      setPending(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger render={<Button variant="outline" size="sm" className="h-7 text-xs" />}>
        <Pencil className="size-3" />
        Edit
      </DialogTrigger>
      <DialogContent>
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>Edit application</DialogTitle>
            <DialogDescription>Adjust the application&apos;s details.</DialogDescription>
          </DialogHeader>

          <div className="mt-4 space-y-3">
            <div className="space-y-1.5">
              <Label htmlFor="edit_company" className="text-xs text-muted-foreground">
                Company
              </Label>
              <Input
                id="edit_company"
                required
                value={company}
                onChange={(e) => setCompany(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="edit_role_title" className="text-xs text-muted-foreground">
                Role
              </Label>
              <Input
                id="edit_role_title"
                required
                value={roleTitle}
                onChange={(e) => setRoleTitle(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="edit_job_url" className="text-xs text-muted-foreground">
                Job URL
              </Label>
              <Input
                id="edit_job_url"
                type="url"
                value={jobUrl}
                onChange={(e) => setJobUrl(e.target.value)}
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="edit_location" className="text-xs text-muted-foreground">
                  Location
                </Label>
                <Input
                  id="edit_location"
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="edit_salary_range" className="text-xs text-muted-foreground">
                  Salary range
                </Label>
                <Input
                  id="edit_salary_range"
                  value={salaryRange}
                  onChange={(e) => setSalaryRange(e.target.value)}
                />
              </div>
            </div>
          </div>

          {error && (
            <p className="mt-3 font-mono text-xs text-destructive" role="alert">
              {error}
            </p>
          )}

          <DialogFooter className="mt-6">
            <Button type="submit" disabled={pending}>
              {pending ? "Saving…" : "Save changes"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
