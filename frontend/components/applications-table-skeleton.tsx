import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const ROW_COUNT = 6;

// Mirrors ApplicationsTable's own two layouts (card list on mobile, table
// on desktop) so the swap from skeleton to real data doesn't reflow.
export function ApplicationsTableSkeleton() {
  return (
    <>
      <div className="space-y-2 md:hidden">
        {Array.from({ length: ROW_COUNT }).map((_, i) => (
          <div
            key={i}
            className="flex items-center justify-between gap-3 rounded-[3px] border border-border bg-card px-4 py-3"
          >
            <div className="min-w-0 flex-1 space-y-2">
              <Skeleton className="h-4 w-2/5" />
              <Skeleton className="h-3.5 w-3/5" />
            </div>
            <Skeleton className="h-5 w-16 shrink-0" />
          </div>
        ))}
      </div>

      <div className="hidden overflow-x-auto rounded-[3px] border border-border md:block">
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              {["Company", "Role", "Stage", "Match", "Location", "Stage since", "Job Posting", "Actions"].map(
                (label) => (
                  <TableHead key={label} className="text-xs font-medium text-muted-foreground">
                    {label}
                  </TableHead>
                ),
              )}
              <TableHead aria-hidden className="w-4 p-0" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {Array.from({ length: ROW_COUNT }).map((_, i) => (
              <TableRow key={i} className="hover:bg-transparent">
                <TableCell className="py-4">
                  <Skeleton className="h-4 w-24" />
                </TableCell>
                <TableCell className="py-4">
                  <Skeleton className="h-4 w-28" />
                </TableCell>
                <TableCell className="py-4">
                  <Skeleton className="h-5 w-20" />
                </TableCell>
                <TableCell className="py-4">
                  <Skeleton className="h-4 w-8" />
                </TableCell>
                <TableCell className="py-4">
                  <Skeleton className="h-4 w-20" />
                </TableCell>
                <TableCell className="py-4">
                  <Skeleton className="h-4 w-16" />
                </TableCell>
                <TableCell className="py-4">
                  <Skeleton className="h-4 w-12" />
                </TableCell>
                <TableCell className="py-4">
                  <div className="flex justify-end gap-2">
                    <Skeleton className="h-6 w-6" />
                    <Skeleton className="h-6 w-6" />
                    <Skeleton className="h-6 w-6" />
                  </div>
                </TableCell>
                <TableCell aria-hidden className="w-4 p-0" />
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </>
  );
}
