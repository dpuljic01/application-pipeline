"use client";

import { useRouter } from "next/navigation";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ArrowDown, ArrowUp, ArrowUpDown, ChevronRight, ExternalLink } from "lucide-react";
import { StageBadge } from "@/components/stage-badge";
import { FollowUpBadge } from "@/components/follow-up-badge";
import { StageChangeMenu } from "@/components/stage-change-menu";
import { EditApplicationDialog } from "@/components/edit-application-dialog";
import { DeleteApplicationDialog } from "@/components/delete-application-dialog";
import { ApplicationCard } from "@/components/application-card";
import { scoreColor } from "@/lib/jd-score";
import { needsFollowUp } from "@/lib/followup";
import type { Application } from "@/lib/types";
import type { SortDirection, SortField } from "@/app/page";

function formatDate(iso: string | null): string {
  return iso ? iso.slice(0, 10) : "—";
}

function SortableTableHead({
  label,
  field,
  sortField,
  sortDirection,
  onSort,
}: {
  label: string;
  field: SortField;
  sortField: SortField | null;
  sortDirection: SortDirection;
  onSort: (field: SortField) => void;
}) {
  const active = field === sortField;
  return (
    <TableHead className="text-xs font-medium text-muted-foreground">
      <button
        type="button"
        onClick={() => onSort(field)}
        className="inline-flex items-center gap-1 hover:text-foreground"
      >
        {label}
        {active ? (
          sortDirection === "asc" ? (
            <ArrowUp className="size-3" />
          ) : (
            <ArrowDown className="size-3" />
          )
        ) : (
          <ArrowUpDown className="size-3 opacity-30" />
        )}
      </button>
    </TableHead>
  );
}

export function ApplicationsTable({
  applications,
  onChanged,
  onDeleted,
  onUnauthorized,
  sortField,
  sortDirection,
  onSort,
}: {
  applications: Application[];
  onChanged: (updated: Application) => void;
  onDeleted: (applicationId: string) => void;
  onUnauthorized: () => void;
  sortField: SortField | null;
  sortDirection: SortDirection;
  onSort: (field: SortField) => void;
}) {
  const router = useRouter();

  if (applications.length === 0) {
    return (
      <div className="rounded-[3px] border border-dashed border-border py-16 text-center">
        <p className="text-sm text-muted-foreground">No applications yet.</p>
        <p className="mt-1 text-xs text-muted-foreground">
          Add one to start tracking the pipeline.
        </p>
      </div>
    );
  }

  return (
    <>
      {/* Mobile: a table with 8 columns doesn't reflow, it just scrolls
          sideways past Actions — a compact tap-through card instead. */}
      <div className="space-y-2 md:hidden">
        {applications.map((application) => (
          <ApplicationCard key={application.id} application={application} />
        ))}
      </div>

      <div className="hidden overflow-x-auto rounded-[3px] border border-border md:block">
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead className="text-xs font-medium text-muted-foreground">
              Company
            </TableHead>
            <TableHead className="text-xs font-medium text-muted-foreground">
              Role
            </TableHead>
            <TableHead className="text-xs font-medium text-muted-foreground">
              Stage
            </TableHead>
            <SortableTableHead
              label="Match"
              field="match_score"
              sortField={sortField}
              sortDirection={sortDirection}
              onSort={onSort}
            />
            <TableHead className="text-xs font-medium text-muted-foreground">
              Location
            </TableHead>
            <SortableTableHead
              label="Stage since"
              field="stage_changed_at"
              sortField={sortField}
              sortDirection={sortDirection}
              onSort={onSort}
            />
            <TableHead className="text-xs font-medium text-muted-foreground">
              Job Posting
            </TableHead>
            <TableHead className="text-right text-xs font-medium text-muted-foreground">
              Actions
            </TableHead>
            <TableHead aria-hidden className="w-4 p-0" />
          </TableRow>
        </TableHeader>
        <TableBody>
          {applications.map((application) => (
            <TableRow
              key={application.id}
              onClick={() => router.push(`/applications/${application.id}`)}
              className="cursor-pointer"
            >
              <TableCell
                className="max-w-[140px] truncate py-4 font-medium"
                title={application.company}
              >
                {application.company}
              </TableCell>
              <TableCell
                className="max-w-[170px] truncate py-4 text-muted-foreground"
                title={application.role_title}
              >
                {application.role_title}
              </TableCell>
              <TableCell className="py-4">
                <div className="flex items-center gap-1.5">
                  <StageBadge stage={application.stage} />
                  {needsFollowUp(application) && <FollowUpBadge />}
                </div>
              </TableCell>
              <TableCell className="py-4 font-mono text-xs tabular-nums">
                {application.match_score !== null ? (
                  <span style={{ color: scoreColor(application.match_score) }}>
                    {application.match_score}
                  </span>
                ) : (
                  <span className="text-muted-foreground">—</span>
                )}
              </TableCell>
              <TableCell
                className="max-w-[130px] truncate py-4 text-muted-foreground"
                title={application.location ?? undefined}
              >
                {application.location ?? "—"}
              </TableCell>
              <TableCell className="py-4 font-mono text-xs text-muted-foreground tabular-nums">
                {formatDate(application.stage_changed_at)}
              </TableCell>
              {/* stopPropagation: this cell has its own link (or nothing to
                  click) — it must not also trigger the row's navigation. */}
              <TableCell className="py-4" onClick={(e) => e.stopPropagation()}>
                {application.job_url ? (
                  <a
                    href={application.job_url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 text-muted-foreground underline decoration-border underline-offset-2 hover:text-foreground hover:decoration-foreground"
                  >
                    View <ExternalLink className="size-3.5" />
                  </a>
                ) : (
                  <span className="text-muted-foreground">—</span>
                )}
              </TableCell>
              {/* Same reasoning: Edit/Change stage/Delete are their own
                  actions, not "open the detail page". */}
              <TableCell
                className="py-4 text-right"
                onClick={(e) => e.stopPropagation()}
              >
                <div className="flex justify-end gap-2">
                  <EditApplicationDialog
                    application={application}
                    onUpdated={onChanged}
                    onUnauthorized={onUnauthorized}
                  />
                  <StageChangeMenu
                    application={application}
                    onChanged={onChanged}
                    onUnauthorized={onUnauthorized}
                  />
                  <DeleteApplicationDialog
                    application={application}
                    onDeleted={onDeleted}
                    onUnauthorized={onUnauthorized}
                  />
                </div>
              </TableCell>
              {/* Visual-only affordance that the row itself is clickable —
                  no stopPropagation here, so it lets the row's onClick fire. */}
              <TableCell className="py-4 pr-3 pl-0 text-muted-foreground">
                <ChevronRight className="size-4" />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      </div>
    </>
  );
}
