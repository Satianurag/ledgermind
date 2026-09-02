"use client";

import { Chip } from "@/components/shell/chip";
import type { StateData } from "@/lib/api";

/**
 * Pinned to the top of the viewport for the whole demo.
 *
 * Rules section 03 requires the fresh-session segment to carry an on-screen timestamp or
 * commit hash. Putting them in a panel means they scroll away mid-take; putting them here
 * means every frame of the recording carries the gate evidence.
 */
export function EvidenceBar({ state }: { state: StateData | null }) {
  const ok = state?.verification.all_ok ?? true;
  const trees = state?.verification.trees ?? 0;

  return (
    <header className="sticky top-0 z-50 border-b border-border/80 bg-background/85 backdrop-blur-md">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-6 gap-y-2 px-6 py-3">
        <div className="flex items-baseline gap-2.5">
          <span className="text-sm font-semibold tracking-tight">Ledgermind</span>
          <span className="text-[11px] text-muted-foreground">Northwind Pay</span>
        </div>

        <div className="h-4 w-px bg-border" />

        <div className="flex items-center gap-2">
          <span className="hash text-xs text-muted-foreground">CASE-2214</span>
          <span className="text-[11px] text-muted-foreground">Meridian payout exception</span>
        </div>

        <div className="ml-auto flex flex-wrap items-center gap-2">
          <Chip tone={ok ? "verified" : "breach"} dot>
            {ok ? `chain intact · ${trees} trees` : `${state?.verification.broken.length} broken`}
          </Chip>
          {state && (
            <>
              <Chip tone="evidence" mono>
                {state.commit}
              </Chip>
              <span className="hash tabular text-[11px] text-muted-foreground">
                {state.timestamp}
              </span>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
