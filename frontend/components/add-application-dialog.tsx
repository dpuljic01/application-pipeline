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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { createApplication, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Application } from "@/lib/types";

export function AddApplicationDialog({
  onCreated,
  onUnauthorized,
}: {
  onCreated: (application: Application) => void;
  onUnauthorized: () => void;
}) {
  const { idToken } = useAuth();
  const [open, setOpen] = useState(false);
  const [company, setCompany] = useState("");
  const [roleTitle, setRoleTitle] = useState("");
  const [jobUrl, setJobUrl] = useState("");
  const [location, setLocation] = useState("");
  const [salaryRange, setSalaryRange] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function reset() {
    setCompany("");
    setRoleTitle("");
    setJobUrl("");
    setLocation("");
    setSalaryRange("");
    setError(null);
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!idToken) return;
    setPending(true);
    setError(null);
    try {
      const application = await createApplication(idToken, {
        company,
        role_title: roleTitle,
        job_url: jobUrl || null,
        location: location || null,
        salary_range: salaryRange || null,
      });
      onCreated(application);
      setOpen(false);
      reset();
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        onUnauthorized();
        return;
      }
      setError(err instanceof Error ? err.message : "Could not add application");
    } finally {
      setPending(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<Button size="sm" />}>
        <Plus className="size-4" />
        Add application
      </DialogTrigger>
      <DialogContent>
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>Add application</DialogTitle>
            <DialogDescription>
              New entries start in the <span className="font-mono">SAVED</span> stage.
            </DialogDescription>
          </DialogHeader>

          <div className="mt-4 space-y-3">
            <div className="space-y-1.5">
              <Label htmlFor="company" className="text-xs text-muted-foreground">
                Company
              </Label>
              <Input
                id="company"
                required
                value={company}
                onChange={(e) => setCompany(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="role_title" className="text-xs text-muted-foreground">
                Role
              </Label>
              <Input
                id="role_title"
                required
                value={roleTitle}
                onChange={(e) => setRoleTitle(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="job_url" className="text-xs text-muted-foreground">
                Job URL
              </Label>
              <Input
                id="job_url"
                type="url"
                value={jobUrl}
                onChange={(e) => setJobUrl(e.target.value)}
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="location" className="text-xs text-muted-foreground">
                  Location
                </Label>
                <Input
                  id="location"
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="salary_range" className="text-xs text-muted-foreground">
                  Salary range
                </Label>
                <Input
                  id="salary_range"
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
              {pending ? "Adding…" : "Add application"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
