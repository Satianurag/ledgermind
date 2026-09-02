"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import type { CongressData } from "@/lib/api";
import { short } from "@/lib/api";

/**
 * The signature beat. Both conflicting versions stay on screen at once -- that is the
 * whole "no last-write-wins" argument, and it has to be visible, not argued.
 */
export function CongressPanel({
  data,
  loading,
  onRun,
}: {
  data: CongressData | null;
  loading: boolean;
  onRun: () => void;
}) {
  const dispute = data?.dispute;
  const winner = dispute?.resolution?.winner_agent;

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <CardTitle>Dispute congress</CardTitle>
            <CardDescription>
              Two agents contradict each other. Neither record is overwritten: a dispute opens
              with both versions visible and resolves with a signed receipt.
            </CardDescription>
          </div>
          <Button size="sm" variant="outline" onClick={onRun} disabled={loading}>
            {loading ? "Running…" : dispute ? "Re-run" : "Open dispute"}
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {!dispute && (
          <p className="text-sm text-muted-foreground">
            Not yet run. The dispute is detected from two conflicting journal records in memory.
          </p>
        )}

        {dispute && (
          <>
            <div className="grid gap-4 md:grid-cols-2">
              {dispute.claimants.map((claimant) => {
                const won = claimant.agent_id === winner;
                return (
                  <div
                    key={claimant.agent_id}
                    className={`rounded-lg border p-4 ${won ? "border-foreground/40 bg-muted/40" : "opacity-80"}`}
                  >
                    <div className="mb-2 flex items-center justify-between gap-2">
                      <span className="font-medium capitalize">{claimant.agent_id}</span>
                      <Badge variant={won ? "secondary" : "outline"} className="text-[10px]">
                        {won ? "upheld" : "superseded"}
                      </Badge>
                    </div>
                    <pre className="overflow-x-auto rounded bg-muted/60 p-2 text-xs">
                      {JSON.stringify(claimant.content, null, 2)}
                    </pre>
                    <p className="mt-2 font-mono text-[11px] text-muted-foreground">
                      {short(claimant.content_hash, 16)}
                    </p>
                  </div>
                );
              })}
            </div>

            <Separator />

            <div className="grid gap-3 text-sm sm:grid-cols-3">
              <div>
                <p className="text-xs text-muted-foreground">Status</p>
                <p className="font-medium">{dispute.status}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Confidence</p>
                <p className="font-medium">{dispute.confidence.toFixed(2)}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Arbiter</p>
                <p className="font-medium">{dispute.resolution?.arbiter_backend ?? "—"}</p>
              </div>
            </div>

            {dispute.resolution && (
              <p className="text-xs text-muted-foreground">
                Cited {dispute.resolution.citations.length} chain-verified tree(s). Citation
                verification failure aborts resolution — the arbiter cannot cite an unverified
                record.
              </p>
            )}

            {dispute.receipt_sig && (
              <div className="rounded-md border bg-muted/30 p-3">
                <p className="text-xs text-muted-foreground">Ed25519 resolution receipt</p>
                <p className="break-all font-mono text-[11px]">{short(dispute.receipt_sig, 64)}</p>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
