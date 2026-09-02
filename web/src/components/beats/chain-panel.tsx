"use client";

import { Chip } from "@/components/shell/chip";
import { Stage } from "@/components/shell/stage";
import type { ChainLink, StateData } from "@/lib/api";
import { TIER_LABEL, hash, trustSemantic } from "@/lib/format";
import { cn } from "@/lib/utils";

const TIER_ORDER = ["hot", "warm", "cold", "reference", "archive"];

function tierOf(tree: string) {
  return tree.split(":", 1)[0];
}

/** Group consecutive links of one tree so the chain reads as chains, not rows. */
function groupByTree(chain: ChainLink[]) {
  const groups: Array<{ tree: string; links: ChainLink[] }> = [];
  for (const link of chain) {
    const last = groups[groups.length - 1];
    if (last && last.tree === link.tree) last.links.push(link);
    else groups.push({ tree: link.tree, links: [link] });
  }
  return groups;
}

export function ChainPanel({ state }: { state: StateData }) {
  const broken = new Set(state.verification.broken.map((b) => b.tree));
  const groups = groupByTree(state.chain).slice(0, 14);

  return (
    <Stage
      eyebrow="Beat 02 · integrity"
      title="Every write is stamped and linked"
      claim="The receipt chain lives inside Sibyl itself — no shadow store. Each entry hashes its predecessor, so altering one body breaks every link after it and verification names the first one."
    >
      <div className="flex flex-wrap items-center gap-2">
        {TIER_ORDER.filter((t) => state.tiers[t]).map((tier) => (
          <Chip key={tier} tone="neutral" mono>
            {TIER_LABEL[tier]} <span className="text-foreground">{state.tiers[tier]}</span>
          </Chip>
        ))}
        <Chip tone="neutral">{state.entity_count} entities</Chip>
        {state.quarantined > 0 && (
          <Chip tone="caution" dot>
            {state.quarantined} quarantined
          </Chip>
        )}
        <Chip tone={state.verification.all_ok ? "verified" : "breach"} dot>
          {state.verification.all_ok
            ? `${state.verification.trees} trees verified`
            : `${state.verification.broken.length} broken`}
        </Chip>
      </div>

      <div className="space-y-3">
        {groups.map(({ tree, links }) => {
          const isBroken = broken.has(tree);
          const tier = tierOf(tree);
          return (
            <div
              key={tree}
              className={cn(
                "rounded-lg border bg-card/60 p-4",
                isBroken ? "border-breach-dim/70 bg-breach-dim/[0.08]" : "border-border",
              )}
            >
              <div className="mb-3 flex flex-wrap items-center gap-2">
                <span className="hash text-[10px] tracking-wider text-muted-foreground">
                  {TIER_LABEL[tier] ?? tier}
                </span>
                <span className="hash text-xs">{tree.split(":").slice(1).join(":")}</span>
                {isBroken && (
                  <Chip tone="breach" dot>
                    link broken
                  </Chip>
                )}
              </div>

              {/* The chain, drawn as one. */}
              <ol className="space-y-0">
                {links.map((link, i) => {
                  const tone = trustSemantic(link.source_trust_tier);
                  return (
                    <li key={link.sequence} className="relative flex gap-3 pb-3 last:pb-0">
                      <div className="flex flex-col items-center">
                        <span
                          className={cn(
                            "mt-1 size-2 shrink-0 rounded-full ring-2 ring-background",
                            isBroken ? "bg-breach" : "bg-verified",
                          )}
                        />
                        {i < links.length - 1 && (
                          <span
                            className={cn(
                              "w-px flex-1",
                              isBroken ? "bg-breach-dim" : "bg-verified-dim/60",
                            )}
                          />
                        )}
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                          <span className="hash tabular text-[11px] text-muted-foreground">
                            #{link.sequence}
                          </span>
                          <span className="text-xs font-medium">{link.agent_id ?? "—"}</span>
                          <Chip tone={tone}>{link.source_trust_tier ?? "—"}</Chip>
                          <span className="hash truncate text-[11px] text-evidence">
                            {hash(link.hash, 10, 6)}
                          </span>
                        </div>
                        {link.evidence_ref && (
                          <p className="mt-0.5 truncate text-[11px] text-muted-foreground">
                            {link.evidence_ref}
                          </p>
                        )}
                      </div>
                    </li>
                  );
                })}
              </ol>
            </div>
          );
        })}
      </div>

      {state.chain.length > 0 && (
        <p className="text-xs text-muted-foreground">
          Showing {groups.length} of {new Set(state.chain.map((c) => c.tree)).size} trees ·{" "}
          {state.chain_length} links total. Export and verify independently with{" "}
          <code className="hash text-foreground">npx ledgermind verify</code>.
        </p>
      )}
    </Stage>
  );
}
