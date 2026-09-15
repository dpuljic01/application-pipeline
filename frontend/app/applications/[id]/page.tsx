"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, ExternalLink } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { getApplication, listActivities, ApiError } from "@/lib/api";
import type { Activity, Application } from "@/lib/types";
import { StageBadge } from "@/components/stage-badge";
import { StageChangeMenu } from "@/components/stage-change-menu";
import { EditApplicationDialog } from "@/components/edit-application-dialog";
import { ActivityTimeline } from "@/components/activity-timeline";
import { AddActivityDialog } from "@/components/add-activity-dialog";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import Link from "next/link";

function formatDate(iso: string | null): string {
  return iso ? iso.slice(0, 10) : "—";
}

export default function ApplicationDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const { idToken, isAuthenticated, isRestoring, logout } = useAuth();

  const [application, setApplication] = useState<Application | null>(null);
  const [activities, setActivities] = useState<Activity[]>([]);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

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

    Promise.all([
      getApplication(idToken, params.id),
      listActivities(idToken, params.id),
    ])
      .then(([app, acts]) => {
        setApplication(app);
        setActivities(acts);
      })
      .catch((err) => {
        if (err instanceof ApiError && err.status === 401) {
          handleUnauthorized();
        } else if (err instanceof ApiError && err.status === 404) {
          setNotFound(true);
        }
      })
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idToken, isAuthenticated, isRestoring, params.id]);

  function handleChanged(updated: Application) {
    setApplication(updated);
  }

  function handleActivityAdded(activity: Activity) {
    setActivities((prev) => [activity, ...prev]);
  }

  if (isRestoring || !isAuthenticated) {
    return null;
  }

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <header className="border-b border-border">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-6 py-4">
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="size-3.5" />
            Back to applications
          </Link>
        </div>
      </header>

      <main className="mx-auto w-full max-w-3xl flex-1 px-6 py-8">
        {loading ? (
          <p className="text-xs text-muted-foreground">Loading…</p>
        ) : notFound || !application ? (
          <div className="rounded-[3px] border border-dashed border-border py-16 text-center">
            <p className="text-sm text-muted-foreground">Application not found.</p>
          </div>
        ) : (
          <>
            <Card className="rounded-[3px]">
              <CardHeader>
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <CardTitle className="text-lg">{application.role_title}</CardTitle>
                    <p className="mt-1 text-sm text-muted-foreground">
                      {application.job_url ? (
                        <a
                          href={application.job_url}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-1 underline decoration-border underline-offset-2 hover:text-foreground hover:decoration-foreground"
                        >
                          {application.company}
                          <ExternalLink className="size-3" />
                        </a>
                      ) : (
                        application.company
                      )}
                    </p>
                  </div>
                  <StageBadge stage={application.stage} />
                </div>
              </CardHeader>
              <CardContent>
                <dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
                  <div>
                    <dt className="text-xs font-medium text-muted-foreground">
                      Location
                    </dt>
                    <dd className="mt-0.5">{application.location ?? "—"}</dd>
                  </div>
                  <div>
                    <dt className="text-xs font-medium text-muted-foreground">
                      Salary range
                    </dt>
                    <dd className="mt-0.5">{application.salary_range ?? "—"}</dd>
                  </div>
                  <div>
                    <dt className="text-xs font-medium text-muted-foreground">
                      Stage since
                    </dt>
                    <dd className="mt-0.5 font-mono text-xs tabular-nums">
                      {formatDate(application.stage_changed_at)}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs font-medium text-muted-foreground">
                      Added
                    </dt>
                    <dd className="mt-0.5 font-mono text-xs tabular-nums">
                      {formatDate(application.created_at)}
                    </dd>
                  </div>
                </dl>

                <div className="mt-5 flex gap-2 border-t border-border pt-4">
                  <EditApplicationDialog
                    application={application}
                    onUpdated={handleChanged}
                    onUnauthorized={handleUnauthorized}
                  />
                  <StageChangeMenu
                    application={application}
                    onChanged={handleChanged}
                    onUnauthorized={handleUnauthorized}
                  />
                </div>
              </CardContent>
            </Card>

            <div className="mt-6">
              <div className="mb-4 flex items-center justify-between">
                <h2 className="text-sm font-medium text-foreground">Notes & timeline</h2>
                <AddActivityDialog
                  applicationId={application.id}
                  onAdded={handleActivityAdded}
                  onUnauthorized={handleUnauthorized}
                />
              </div>
              <ActivityTimeline activities={activities} />
            </div>
          </>
        )}
      </main>
    </div>
  );
}
