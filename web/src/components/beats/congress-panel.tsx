"use client";

import { Button } from "@/components/ui/button";
import { Chip, Label } from "@/components/shell/chip";
import { Stage } from "@/components/shell/stage";
import type { CongressData } from "@/lib/api";
import { hash } from "@/lib/format";
import { cn } from "@/lib/utils";

/**
 * The signature beat. Both versions stay on screen, one upheld and one superseded —
 * that is the no-last-write-wins argument, and it has to be seen rather than read.
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
    <Stage
      eyebrow="Beat 03 · adjudication"
      title="Two agents disagree. Neither record is destroyed."
      claim="Last-write-wins would silently overwrite the earlier claim and lose the conflict. Instead a dispute opens holding both versions, the arbiter may cite only chain-verified records, and the resolution is signed."
      action={
        <Button size="sm" variant={dispute ? "outline" : "default"} onClick={onRun} disabled={loading}>
          {loading ? "Adjudicating…" : dispute ? "Re-run" : "Open dispute"}
        </Button>
      }
    >
      {!dispute && (
        <div className="rounded-lg border border-dashed border-border px-6 py-12 text-center">
          <p className="text-sm text-muted-foreground">
            The dispute is detected by comparing two journal records in memory —
            it is not scripted.
          </p>
        </div>
      )}

      {dispute && (
        <>
          <div className="grid gap-4 md:grid-cols-[1fr_auto_1fr] md:items-stretch">
            {dispute.claimants.map((claimant, i) => {
              const won = claimant.agent_id === winner;
              const status = String(
                (claimant.content as { status?: string }).status ?? "—",
              );
              return [
                i === 1 && (
                  <div key="vs" className="hidden items-center justify-center md:flex">
                    <span className="hash text-[10px] uppercase tracking-widest text-muted-foreground">
                      vs
                    </span>
                  </div>
                ),
                <div
                  key={claimant.agent_id}
                  className={cn(
                    "flex flex-col rounded-lg border p-5 transition-colors",
                    won
                      ? "border-verified-dim/70 bg-verified-dim/[0.08]"
                      : "border-border bg-card/40",
                  )}
                >
                  <div className="mb-4 flex items-center justify-between gap-2">
                    <span className="text-sm font-medium capitalize">{claimant.agent_id}</span>
                    <Chip tone={won ? "verified" : "neutral"} dot={won}>
                      {won ? "upheld" : "superseded"}
                    </Chip>
                  </div>

                  <p
                    className={cn(
                      "text-2xl font-semibold tracking-tight",
                      won ? "text-verified" : "text-muted-foreground line-through decoration-1",
                    )}
                  >
                    {status}
                  </p>

                  <div className="mt-auto pt-4">
                    <Label>Content hash</Label>
                    <p className="hash mt-1 text-[11px] text-muted-foreground">
                      {hash(claimant.content_hash, 12, 8)}
                    </p>
                  </div>
                </div>,
              ];
            })}
          </div>

          <div className="grid gap-px overflow-hidden rounded-lg border border-border bg-border sm:grid-cols-3">
            {[
              { label: "Status", value: dispute.status },
              { label: "Confidence", value: dispute.confidence.toFixed(2) },
              { label: "Arbiter", value: dispute.resolution?.arbiter_backend ?? "—" },
            ].map((cell) => (
              <div key={cell.label} className="bg-card px-4 py-3">
                <Label>{cell.label}</Label>
                <p className="mt-1 text-sm font-medium">{cell.value}</p>
              </div>
            ))}
          </div>

          {dispute.resolution && (
            <p className="text-xs leading-relaxed text-muted-foreground">
              Cited {dispute.resolution.citations.length} chain-verified tree(s). A citation that
              fails verification aborts the resolution — the arbiter cannot cite a record it
              cannot prove.
            </p>
          )}

          {dispute.receipt_sig && (
            <div className="rounded-lg border border-evidence-dim/50 bg-evidence-dim/[0.07] p-4">
              <Label>Ed25519 resolution receipt</Label>
              <p className="hash mt-1.5 break-all text-[11px] text-evidence">
                {dispute.receipt_sig}
              </p>
            </div>
          )}
        </>
      )}
    </Stage>
  );
}
