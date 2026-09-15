"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { listApplications, ApiError } from "@/lib/api";
import { APPLICATION_STAGES } from "@/lib/types";
import type { Application, ApplicationStage } from "@/lib/types";
import { ApplicationsTable } from "@/components/applications-table";
import { StatsRow } from "@/components/stats-row";
import { StageBreakdown } from "@/components/stage-breakdown";
import { AddApplicationDialog } from "@/components/add-application-dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export default function DashboardPage() {
  const router = useRouter();
  const { idToken, email, isAuthenticated, logout } = useAuth();

  const [applications, setApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [stageFilter, setStageFilter] = useState<ApplicationStage | "ALL">("ALL");

  function handleUnauthorized() {
    logout();
    router.push("/login");
  }

  useEffect(() => {
    if (!isAuthenticated) {
      router.push("/login");
      return;
    }
    if (!idToken) return;

    listApplications(idToken)
      .then(setApplications)
      .catch((err) => {
        if (err instanceof ApiError && err.status === 401) {
          handleUnauthorized();
        }
      })
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idToken, isAuthenticated]);

  const filtered = useMemo(() => {
    return applications.filter((app) => {
      const matchesStage = stageFilter === "ALL" || app.stage === stageFilter;
      const query = search.trim().toLowerCase();
      const matchesSearch =
        query.length === 0 ||
        app.company.toLowerCase().includes(query) ||
        app.role_title.toLowerCase().includes(query);
      return matchesStage && matchesSearch;
    });
  }, [applications, search, stageFilter]);

  function handleCreated(application: Application) {
    setApplications((prev) => [application, ...prev]);
  }

  function handleChanged(updated: Application) {
    setApplications((prev) => prev.map((app) => (app.id === updated.id ? updated : app)));
  }

  function handleDeleted(applicationId: string) {
    setApplications((prev) => prev.filter((app) => app.id !== applicationId));
  }

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <header className="border-b border-border">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div>
            <p className="font-mono text-base font-medium tracking-[0.15em] text-foreground uppercase">
              Application Pipeline
            </p>
            {email && <p className="mt-0.5 text-xs text-muted-foreground">{email}</p>}
          </div>
          <Button variant="ghost" size="sm" onClick={handleUnauthorized}>
            Sign out
          </Button>
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-8">
        <StatsRow applications={applications} />
        <div className="mb-5">
          <StageBreakdown applications={applications} />
        </div>

        <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <h1 className="flex items-center gap-2 text-sm text-muted-foreground">
              Applications
              <span className="rounded-[3px] bg-muted px-1.5 py-0.5 font-mono text-xs text-foreground tabular-nums">
                {applications.length}
              </span>
            </h1>
          </div>
          <AddApplicationDialog onCreated={handleCreated} onUnauthorized={handleUnauthorized} />
        </div>

        <div className="mb-4 flex flex-wrap items-center gap-2">
          <Input
            placeholder="Search company or role…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="max-w-xs"
          />
          <Select
            value={stageFilter}
            onValueChange={(value) => setStageFilter(value as ApplicationStage | "ALL")}
          >
            <SelectTrigger className="w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="ALL">All stages</SelectItem>
              {APPLICATION_STAGES.map((stage) => (
                <SelectItem key={stage} value={stage}>
                  {stage}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {loading ? (
          <p className="font-mono text-xs text-muted-foreground">Loading…</p>
        ) : (
          <ApplicationsTable
            applications={filtered}
            onChanged={handleChanged}
            onDeleted={handleDeleted}
            onUnauthorized={handleUnauthorized}
          />
        )}
      </main>
    </div>
  );
}
