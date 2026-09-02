"use client";

import { Button } from "@/components/ui/button";
import { Chip, Label } from "@/components/shell/chip";
import { Stage } from "@/components/shell/stage";
import type { SettlementData } from "@/lib/api";
import { hash } from "@/lib/format";
import { cn } from "@/lib/utils";

const KIND_LABEL: Record<string, string> = {
  x402: "x402 payment",
  b20: "B20 read",
  acp: "Virtuals ACP job",
  checkpoint: "chain-head anchor",
};

export function SettlementPanel({
  data,
  loading,
  onRun,
}: {
  data: SettlementData | null;
  loading: boolean;
  onRun: () => void;
}) {
  return (
    <Stage
      eyebrow="Beat 05 · settlement"
      title="Real money, governed by remembered policy"
      claim="The spend cap is not a constant in the code. It is read from the REFERENCE tier before every payment, so changing the remembered policy changes what the wallet is allowed to do."
      action={
        <Button size="sm" variant={data ? "outline" : "default"} onClick={onRun} disabled={loading}>
          {loading ? "Loading…" : data ? "Refresh" : "Load receipts"}
        </Button>
      }
    >
      {!data && (
        <div className="rounded-lg border border-dashed border-border px-6 py-12 text-center">
          <p className="text-sm text-muted-foreground">
            Receipts are written back into governed memory as COLD events and REFERENCE records.
          </p>
        </div>
      )}

      {data && (
        <>
          <div>
            <Label className="mb-3 block">Onchain evidence</Label>
            <div className="divide-y divide-border overflow-hidden rounded-lg border border-border">
              {data.receipts.map((r) => (
                <div key={r.kind} className="flex flex-wrap items-center gap-3 bg-card/40 px-4 py-3">
                  <Chip tone="verified" dot>
                    executed
                  </Chip>
                  <span className="text-sm font-medium">{KIND_LABEL[r.kind] ?? r.kind}</span>
                  <span className="text-xs text-muted-foreground">
                    {r.amount_usdc ? `${r.amount_usdc} USDC · ` : ""}
                    {r.network ?? "base"}
                  </span>
                  {r.explorer_url && (
                    <a
                      href={r.explorer_url}
                      target="_blank"
                      rel="noreferrer"
                      className="hash ml-auto text-[11px] text-evidence underline-offset-4 hover:underline"
                    >
                      {r.tx_hash ? hash(r.tx_hash, 10, 8) : "explorer ↗"}
                    </a>
                  )}
                </div>
              ))}
              {data.unexercised_stacks.map((s) => (
                <div key={s} className="flex flex-wrap items-center gap-3 bg-card/20 px-4 py-3">
                  <Chip tone="neutral">not exercised</Chip>
                  <span className="text-sm text-muted-foreground">{KIND_LABEL[s] ?? s}</span>
                  <span className="ml-auto text-[11px] text-muted-foreground">
                    reported as absent, never synthesised
                  </span>
                </div>
              ))}
            </div>
          </div>

          {data.cap_check_over && (
            <div className="grid gap-px overflow-hidden rounded-lg border border-border bg-border sm:grid-cols-2">
              {[
                { amount: "$2.50", check: data.cap_check_over },
                { amount: "$0.50", check: data.cap_check_under },
              ].map(
                (row) =>
                  row.check && (
                    <div key={row.amount} className="bg-card px-4 py-3.5">
                      <div className="flex items-center justify-between gap-2">
                        <span className="hash tabular text-sm">{row.amount}</span>
                        <Chip tone={row.check.allowed ? "verified" : "breach"} dot>
                          {row.check.allowed ? "allowed" : "refused"}
                        </Chip>
                      </div>
                      <p className="mt-1.5 text-[11px] text-muted-foreground">
                        {row.check.allowed
                          ? `within the remembered cap`
                          : (row.check as { reason?: string }).reason}
                      </p>
                    </div>
                  ),
              )}
            </div>
          )}

          <div
            className={cn(
              "overflow-hidden rounded-lg border",
              data.flip.flipped ? "border-verified-dim/50" : "border-border",
            )}
          >
            <div className="px-5 py-4">
              <Label>Commercial decision</Label>
              <p className="mt-1.5 text-xl font-semibold tracking-tight">{data.decision}</p>
              <p className="mt-1 text-sm text-muted-foreground">{data.why}</p>
            </div>
            <div className="border-t border-border bg-card/40 px-5 py-3.5">
              <Label>Counterfactual replay</Label>
              <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                {data.flip.explanation}
              </p>
              {data.flip.removed_content_hash && (
                <p className="hash mt-1.5 text-[11px] text-evidence">
                  {hash(data.flip.removed_content_hash, 12, 8)}
                </p>
              )}
            </div>
          </div>
        </>
      )}
    </Stage>
  );
}
