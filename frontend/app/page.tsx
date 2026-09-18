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
import { AppHeader } from "@/components/app-header";
import { LoadingScreen } from "@/components/loading-screen";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

// The only fields a column header can be clicked to sort by. `null` means
// "no header is active" — the default order (newest saved first) applies,
// same as the backend's own default `ORDER BY created_at DESC`.
export type SortField = "match_score" | "stage_changed_at";
export type SortDirection = "asc" | "desc";

function compareApplications(
  a: Application,
  b: Application,
  field: SortField | null,
  direction: SortDirection,
): number {
  if (field === null) {
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
  }

  const sign = direction === "asc" ? 1 : -1;

  if (field === "match_score") {
    // Unscored applications always sort last, regardless of direction —
    // null isn't "low", it's "unknown", so it shouldn't outrank a real 0.
    if (a.match_score === null && b.match_score === null) return 0;
    if (a.match_score === null) return 1;
    if (b.match_score === null) return -1;
    return (a.match_score - b.match_score) * sign;
  }

  if (a.stage_changed_at === null && b.stage_changed_at === null) return 0;
  if (a.stage_changed_at === null) return 1;
  if (b.stage_changed_at === null) return -1;
  return (
    (new Date(a.stage_changed_at).getTime() - new Date(b.stage_changed_at).getTime()) *
    sign
  );
}

export default function DashboardPage() {
  const router = useRouter();
  const { idToken, email, isAuthenticated, isRestoring, logout } = useAuth();

  const [applications, setApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [stageFilter, setStageFilter] = useState<ApplicationStage | "ALL">("ALL");
  // null = default order (newest saved first, matches the backend default).
  const [sortField, setSortField] = useState<SortField | null>(null);
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");

  // Three-state cycle per header: unsorted -> desc -> asc -> unsorted.
  function handleSort(field: SortField) {
    if (field !== sortField) {
      setSortField(field);
      setSortDirection("desc");
    } else if (sortDirection === "desc") {
      setSortDirection("asc");
    } else {
      setSortField(null);
    }
  }

  function handleUnauthorized() {
    logout();
    router.push("/login");
  }

  useEffect(() => {
    if (isRestoring) return;
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
  }, [idToken, isAuthenticated, isRestoring]);

  const filtered = useMemo(() => {
    const matches = applications.filter((app) => {
      const matchesStage = stageFilter === "ALL" || app.stage === stageFilter;
      const query = search.trim().toLowerCase();
      const matchesSearch =
        query.length === 0 ||
        app.company.toLowerCase().includes(query) ||
        app.role_title.toLowerCase().includes(query);
      return matchesStage && matchesSearch;
    });
    return [...matches].sort((a, b) =>
      compareApplications(a, b, sortField, sortDirection),
    );
  }, [applications, search, stageFilter, sortField, sortDirection]);

  function handleCreated(application: Application) {
    setApplications((prev) => [application, ...prev]);
  }

  function handleChanged(updated: Application) {
    setApplications((prev) => prev.map((app) => (app.id === updated.id ? updated : app)));
  }

  function handleDeleted(applicationId: string) {
    setApplications((prev) => prev.filter((app) => app.id !== applicationId));
  }

  if (isRestoring) {
    return <LoadingScreen />;
  }

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <AppHeader email={email} onSignOut={handleUnauthorized} />

      <main className="mx-auto w-full max-w-7xl flex-1 px-6 py-8">
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
            sortField={sortField}
            sortDirection={sortDirection}
            onSort={handleSort}
          />
        )}
      </main>
    </div>
  );
}
