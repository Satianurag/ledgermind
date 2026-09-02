"use client";

import { Button } from "@/components/ui/button";
import { Chip, Label } from "@/components/shell/chip";
import { Stage } from "@/components/shell/stage";
import type { InjectData, RollbackData, StateData } from "@/lib/api";
import { trustSemantic } from "@/lib/format";
import { cn } from "@/lib/utils";

const PATH_META: Record<string, { label: string; note: string; counted: boolean }> = {
  "source-trust": {
    label: "Source trust",
    note: "provenance below threshold → quarantined",
    counted: true,
  },
  "chain-integrity": {
    label: "Chain integrity",
    note: "verification failed on the written tree",
    counted: true,
  },
  "content-heuristic": {
    label: "Content heuristic",
    note: "keyword match — advisory only, never counted as caught",
    counted: false,
  },
};

export function HeistPanel({
  cards,
  result,
  rollback,
  busy,
  onInject,
  onRollback,
}: {
  cards: StateData["poison_cards"];
  result: InjectData | null;
  rollback: RollbackData | null;
  busy: boolean;
  onInject: (id: string) => void;
  onRollback: () => void;
}) {
  return (
    <Stage
      eyebrow="Beat 04 · adversarial"
      title="Inject a poisoned fact and watch what actually catches it"
      claim="Each path is reported as what it is. A keyword match is labelled advisory and never counts as a catch — content screening cannot detect a plainly worded false assertion, and pretending otherwise is how a defense looks stronger than it is."
    >
      <div>
        <Label className="mb-3 block">Pick an injection</Label>
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {cards.map((card) => {
            const tone = trustSemantic(card.tier);
            const selected = result?.card.id === card.id;
            return (
              <button
                key={card.id}
                onClick={() => onInject(card.id)}
                disabled={busy}
                className={cn(
                  "rounded-lg border p-3 text-left transition-colors disabled:opacity-50",
                  selected ? "border-foreground/40 bg-card" : "border-border bg-card/40 hover:bg-card",
                )}
              >
                <div className="mb-1.5 flex items-center justify-between gap-2">
                  <span className="text-xs font-medium">{card.label}</span>
                  <Chip tone={tone}>{card.tier}</Chip>
                </div>
                <p className="line-clamp-2 text-[11px] leading-snug text-muted-foreground">
                  {card.text}
                </p>
              </button>
            );
          })}
        </div>
      </div>

      {result && (
        <div
          className={cn(
            "overflow-hidden rounded-lg border",
            result.verdict.caught
              ? "border-verified-dim/60 bg-verified-dim/[0.07]"
              : "border-breach-dim/60 bg-breach-dim/[0.07]",
          )}
        >
          <div className="flex flex-wrap items-center gap-3 border-b border-border/60 px-5 py-4">
            <span
              className={cn(
                "text-lg font-semibold tracking-tight",
                result.verdict.caught ? "text-verified" : "text-breach",
              )}
            >
              {result.verdict.caught ? "Caught" : "Not caught"}
            </span>
            <span className="text-xs text-muted-foreground">“{result.card.text}”</span>
          </div>

          <div className="divide-y divide-border/60">
            {Object.entries(PATH_META).map(([key, meta]) => {
              const fired = result.verdict.paths_fired.includes(key);
              return (
                <div key={key} className="flex items-start gap-3 px-5 py-3">
                  <span
                    className={cn(
                      "mt-0.5 size-1.5 shrink-0 rounded-full",
                      fired
                        ? meta.counted
                          ? "bg-verified"
                          : "bg-caution"
                        : "bg-muted-foreground/30",
                    )}
                  />
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span
                        className={cn(
                          "text-xs font-medium",
                          fired ? "text-foreground" : "text-muted-foreground",
                        )}
                      >
                        {meta.label}
                      </span>
                      {fired && !meta.counted && <Chip tone="caution">advisory</Chip>}
                      {!fired && <span className="text-[11px] text-muted-foreground">idle</span>}
                    </div>
                    <p className="mt-0.5 text-[11px] text-muted-foreground">{meta.note}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-3 rounded-lg border border-border bg-card/40 px-4 py-3">
        <Button size="sm" variant="secondary" onClick={onRollback} disabled={busy}>
          Roll back to checkpoint
        </Button>
        <span className="text-xs text-muted-foreground">
          {rollback
            ? rollback.result.restored
              ? `restored ${rollback.result.restored_entities} entities`
              : rollback.result.reason
            : "restores tier state to the last captured checkpoint"}
        </span>
      </div>
    </Stage>
  );
}
