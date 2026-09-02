"use client";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableRow } from "@/components/ui/table";
import type { RecallData } from "@/lib/api";
import { short } from "@/lib/api";

/**
 * The gate. Rules section 03 requires cold-start recall in one continuous unedited segment
 * with an on-screen timestamp or commit hash, so both are rendered large and always visible.
 */
export function RecallPanel({ data }: { data: RecallData }) {
  const cp = (data.counterparty ?? {}) as Record<string, unknown>;

  return (
    <Card className="border-foreground/25">
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <CardTitle>Fresh-session recall</CardTitle>
            <CardDescription>
              A cold start reads this back out of Sibyl and changes the commercial decision
              because of it.
            </CardDescription>
          </div>
          <div className="text-right">
            <p className="font-mono text-sm font-medium">{data.commit}</p>
            <p className="font-mono text-xs text-muted-foreground">{data.timestamp}</p>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <Table>
          <TableBody>
            <TableRow>
              <TableCell className="w-[40%] text-xs text-muted-foreground">
                Assignment (HOT)
              </TableCell>
              <TableCell className="text-sm">
                {(data.priority as { task?: string })?.task ?? "—"}
              </TableCell>
            </TableRow>
            <TableRow>
              <TableCell className="text-xs text-muted-foreground">Counterparty (WARM)</TableCell>
              <TableCell className="text-sm">
                {String(cp.name ?? "—")}
                {cp.late_deliveries !== undefined && (
                  <span className="text-muted-foreground">
                    {" "}
                    · {String(cp.late_deliveries)} late, {String(cp.overcharges)} overcharge ·
                    reliability {String(cp.reliability_score)}
                  </span>
                )}
              </TableCell>
            </TableRow>
            <TableRow>
              <TableCell className="text-xs text-muted-foreground">Content hash</TableCell>
              <TableCell className="font-mono text-xs">
                {short(data.counterparty_hash, 32)}
              </TableCell>
            </TableRow>
            <TableRow>
              <TableCell className="text-xs text-muted-foreground">Journal (COLD)</TableCell>
              <TableCell className="text-sm">{data.events} events</TableCell>
            </TableRow>
          </TableBody>
        </Table>

        <Alert>
          <AlertTitle className="flex flex-wrap items-center gap-2">
            {data.decision}
            {data.counterfactual.flipped && (
              <Badge variant="secondary" className="text-[10px]">
                flipped by memory
              </Badge>
            )}
          </AlertTitle>
          <AlertDescription className="space-y-1">
            <span className="block">{data.why}</span>
            <span className="block text-xs text-muted-foreground">
              {data.counterfactual.explanation}
            </span>
          </AlertDescription>
        </Alert>
      </CardContent>
    </Card>
  );
}
