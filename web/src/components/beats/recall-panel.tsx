"use client";

import { Chip, Label } from "@/components/shell/chip";
import { Stage } from "@/components/shell/stage";
import type { RecallData } from "@/lib/api";
import { hash } from "@/lib/format";

/** The gate beat. The decision is the hero; everything else is the evidence for it. */
export function RecallPanel({ data }: { data: RecallData }) {
  const cp = (data.counterparty ?? {}) as Record<string, unknown>;
  const priority = (data.priority ?? {}) as Record<string, unknown>;
  const flipped = data.counterfactual.flipped;

  const recalled = [
    { tier: "HOT", label: "Assignment", value: String(priority.task ?? "—") },
    {
      tier: "WARM",
      label: "Counterparty",
      value: `${String(cp.name ?? "—")}`,
      detail:
        cp.late_deliveries !== undefined
          ? `${cp.late_deliveries} late · ${cp.overcharges} overcharge · reliability ${cp.reliability_score}`
          : undefined,
    },
    { tier: "COLD", label: "Journal", value: `${data.events} events` },
    {
      tier: "REFERENCE",
      label: "Policy",
      value: `dual approval above $${Number(
        (data.policy as { dual_approval_threshold_usd?: number })?.dual_approval_threshold_usd ?? 0,
      ).toLocaleString()}`,
    },
  ];

  return (
    <Stage
      eyebrow="Beat 01 · the gate"
      title="A cold session recalls, and the decision changes"
      claim="Nothing is carried over in process memory. This session opened, read four tiers out of Sibyl, and reached a different commercial answer than it would have with an empty store."
    >
      {/* The outcome, given the weight it deserves. */}
      <div className="overflow-hidden rounded-lg border border-verified-dim/50 bg-verified-dim/[0.07]">
        <div className="flex flex-wrap items-start justify-between gap-4 p-6">
          <div className="space-y-2">
            <Label>Commercial decision</Label>
            <p className="text-3xl font-semibold tracking-tight">
              {data.decision.replace(/\s*\(.*\)$/, "")}
            </p>
            <p className="text-sm text-muted-foreground">
              {data.decision.match(/\((.*)\)/)?.[1] ?? ""}
            </p>
          </div>
          {flipped && (
            <Chip tone="verified" dot>
              flipped by recalled memory
            </Chip>
          )}
        </div>
        <div className="border-t border-verified-dim/30 bg-background/40 px-6 py-4">
          <p className="text-sm leading-relaxed">{data.why}</p>
          <p className="mt-2 text-xs leading-relaxed text-muted-foreground">
            {data.counterfactual.explanation}
          </p>
        </div>
      </div>

      {/* What it read, tier by tier. */}
      <div>
        <Label className="mb-3 block">Recalled from Sibyl this session</Label>
        <div className="divide-y divide-border/70 overflow-hidden rounded-lg border border-border">
          {recalled.map((row) => (
            <div key={row.label} className="flex flex-wrap items-baseline gap-x-4 gap-y-1 px-4 py-3">
              <span className="hash w-20 shrink-0 text-[10px] tracking-wider text-muted-foreground">
                {row.tier}
              </span>
              <span className="w-28 shrink-0 text-xs text-muted-foreground">{row.label}</span>
              <span className="flex-1 text-sm">
                {row.value}
                {row.detail && (
                  <span className="ml-2 text-xs text-muted-foreground">{row.detail}</span>
                )}
              </span>
            </div>
          ))}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-x-6 gap-y-2 rounded-lg border border-border bg-card px-4 py-3">
        <div className="space-y-0.5">
          <Label>Commit</Label>
          <p className="hash text-sm">{data.commit}</p>
        </div>
        <div className="space-y-0.5">
          <Label>Session opened</Label>
          <p className="hash tabular text-sm">{data.timestamp}</p>
        </div>
        <div className="min-w-0 space-y-0.5">
          <Label>Deciding memory item</Label>
          <p className="hash truncate text-sm text-evidence">{hash(data.counterparty_hash, 12, 8)}</p>
        </div>
      </div>
    </Stage>
  );
}
