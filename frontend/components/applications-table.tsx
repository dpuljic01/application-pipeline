import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ExternalLink } from "lucide-react";
import { StageBadge } from "@/components/stage-badge";
import { StageChangeMenu } from "@/components/stage-change-menu";
import { EditApplicationDialog } from "@/components/edit-application-dialog";
import type { Application } from "@/lib/types";

function formatDate(iso: string | null): string {
  return iso ? iso.slice(0, 10) : "—";
}

export function ApplicationsTable({
  applications,
  onChanged,
  onUnauthorized,
}: {
  applications: Application[];
  onChanged: (updated: Application) => void;
  onUnauthorized: () => void;
}) {
  if (applications.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-border py-16 text-center">
        <p className="text-sm text-muted-foreground">No applications yet.</p>
        <p className="mt-1 font-mono text-xs text-muted-foreground">
          Add one to start tracking the pipeline.
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead className="font-mono text-[11px] tracking-wider text-muted-foreground uppercase">
              Company
            </TableHead>
            <TableHead className="font-mono text-[11px] tracking-wider text-muted-foreground uppercase">
              Role
            </TableHead>
            <TableHead className="font-mono text-[11px] tracking-wider text-muted-foreground uppercase">
              Stage
            </TableHead>
            <TableHead className="font-mono text-[11px] tracking-wider text-muted-foreground uppercase">
              Location
            </TableHead>
            <TableHead className="font-mono text-[11px] tracking-wider text-muted-foreground uppercase">
              Stage since
            </TableHead>
            <TableHead className="font-mono text-[11px] tracking-wider text-muted-foreground uppercase">
              Job Posting
            </TableHead>
            <TableHead className="text-right font-mono text-[11px] tracking-wider text-muted-foreground uppercase">
              Actions
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {applications.map((application) => (
            <TableRow key={application.id}>
              <TableCell className="py-4 font-medium">
                {application.job_url ? (
                  <a
                    href={application.job_url}
                    target="_blank"
                    rel="noreferrer"
                    className="underline decoration-border underline-offset-2 hover:decoration-foreground"
                  >
                    {application.company}
                  </a>
                ) : (
                  application.company
                )}
              </TableCell>
              <TableCell className="py-4 text-muted-foreground">
                {application.role_title}
              </TableCell>
              <TableCell className="py-4">
                <StageBadge stage={application.stage} />
              </TableCell>
              <TableCell className="py-4 text-muted-foreground">
                {application.location ?? "—"}
              </TableCell>
              <TableCell className="py-4 font-mono text-xs text-muted-foreground tabular-nums">
                {formatDate(application.stage_changed_at)}
              </TableCell>
              <TableCell className="py-4">
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
              <TableCell className="py-4 text-right">
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
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
