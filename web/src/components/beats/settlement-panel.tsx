"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import type { SettlementData } from "@/lib/api";
import { short } from "@/lib/api";

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
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <CardTitle>Settlement on Base</CardTitle>
            <CardDescription>
              Live receipts written back into governed memory, and the spend cap read from the
              REFERENCE tier before any payment.
            </CardDescription>
          </div>
          <Button size="sm" variant="outline" onClick={onRun} disabled={loading}>
            {loading ? "Loading…" : data ? "Refresh" : "Load receipts"}
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {!data && <p className="text-sm text-muted-foreground">Not yet loaded.</p>}

        {data && (
          <>
            <div className="space-y-2">
              {data.receipts.map((receipt) => (
                <div
                  key={receipt.kind}
                  className="flex flex-wrap items-center justify-between gap-2 rounded-md border p-3"
                >
                  <div className="flex items-center gap-2">
                    <Badge variant="secondary" className="uppercase">
                      {receipt.kind}
                    </Badge>
                    <span className="text-xs text-muted-foreground">
                      {receipt.amount_usdc ? `${receipt.amount_usdc} USDC · ` : ""}
                      {receipt.network ?? "base"}
                    </span>
                  </div>
                  {receipt.explorer_url && (
                    <a
                      className="font-mono text-[11px] underline underline-offset-2"
                      href={receipt.explorer_url}
                      target="_blank"
                      rel="noreferrer"
                    >
                      {receipt.tx_hash ? short(receipt.tx_hash, 18) : "explorer"}
                    </a>
                  )}
                </div>
              ))}
              {data.unexercised_stacks.map((stack) => (
                <div key={stack} className="rounded-md border border-dashed p-3 text-xs text-muted-foreground">
                  <span className="font-mono uppercase">{stack}</span> — not exercised in this
                  checkout. Reported as absent rather than synthesised.
                </div>
              ))}
            </div>

            {data.cap_check_over && (
              <div className="rounded-md border bg-muted/30 p-3 text-xs">
                <p className="mb-1 font-medium">Memory-governed wallet cap</p>
                <p className="text-muted-foreground">
                  {data.cap_check_over.allowed ? "allowed" : data.cap_check_over.reason} — cap read
                  from <code>{data.cap_check_over.policy_key}</code> in the REFERENCE tier before
                  the payment, not from a constant.
                </p>
              </div>
            )}

            <Separator />

            <div className="space-y-2">
              <p className="text-xs text-muted-foreground">Commercial decision</p>
              <p className="text-lg font-medium">{data.decision}</p>
              <p className="text-sm text-muted-foreground">{data.why}</p>
            </div>

            <div className="rounded-md border-l-2 border-foreground/30 bg-muted/30 p-3">
              <p className="text-xs font-medium">Counterfactual replay</p>
              <p className="mt-1 text-xs text-muted-foreground">{data.flip.explanation}</p>
              {data.flip.removed_content_hash && (
                <p className="mt-1 font-mono text-[11px]">
                  cited item {short(data.flip.removed_content_hash, 24)}
                </p>
              )}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
