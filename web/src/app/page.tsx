"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { ChainPanel } from "@/components/beats/chain-panel";
import { CongressPanel } from "@/components/beats/congress-panel";
import { HeistPanel } from "@/components/beats/heist-panel";
import { RecallPanel } from "@/components/beats/recall-panel";
import { SettlementPanel } from "@/components/beats/settlement-panel";
import { BeatRail, type Beat, type BeatId } from "@/components/shell/beat-rail";
import { EvidenceBar } from "@/components/shell/evidence-bar";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import {
  api,
  type CongressData,
  type InjectData,
  type RecallData,
  type RollbackData,
  type SettlementData,
  type StateData,
} from "@/lib/api";

export default function Home() {
  const [state, setState] = useState<StateData | null>(null);
  const [recall, setRecall] = useState<RecallData | null>(null);
  const [congress, setCongress] = useState<CongressData | null>(null);
  const [settlement, setSettlement] = useState<SettlementData | null>(null);
  const [inject, setInject] = useState<InjectData | null>(null);
  const [rollback, setRollback] = useState<RollbackData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [loadingBeat, setLoadingBeat] = useState<BeatId | null>(null);
  const [active, setActive] = useState<BeatId>("recall");

  const refresh = useCallback(async () => {
    try {
      const [s, r] = await Promise.all([api.state(), api.recall()]);
      setState(s);
      setRecall(r);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([api.state(), api.recall()])
      .then(([s, r]) => {
        if (controller.signal.aborted) return;
        setState(s);
        setRecall(r);
        setError(null);
      })
      .catch((err: unknown) => {
        if (controller.signal.aborted) return;
        setError(err instanceof Error ? err.message : String(err));
      });
    return () => controller.abort();
  }, []);

  const beats: Beat[] = useMemo(
    () => [
      {
        id: "recall",
        index: "1",
        title: "Fresh recall",
        caption: "cold start changes the decision",
        done: Boolean(recall),
      },
      {
        id: "chain",
        index: "2",
        title: "Receipt chain",
        caption: "provenance and tamper-evidence",
        done: Boolean(state),
      },
      {
        id: "congress",
        index: "3",
        title: "Dispute congress",
        caption: "both versions survive",
        done: Boolean(congress),
      },
      {
        id: "heist",
        index: "4",
        title: "The heist",
        caption: "poison injection",
        done: Boolean(inject),
      },
      {
        id: "settlement",
        index: "5",
        title: "Settlement",
        caption: "capped spend on Base",
        done: Boolean(settlement),
      },
    ],
    [recall, state, congress, inject, settlement],
  );

  const onInject = async (cardId: string) => {
    setBusy(true);
    try {
      const result = await api.inject(cardId);
      setInject(result);
      toast[result.verdict.caught ? "success" : "error"](
        result.verdict.caught ? "Poison caught" : "Poison NOT caught",
        { description: result.verdict.detail },
      );
      await refresh();
    } catch (err) {
      toast.error("Injection failed", {
        description: err instanceof Error ? err.message : String(err),
      });
    } finally {
      setBusy(false);
    }
  };

  const onRollback = async () => {
    setBusy(true);
    try {
      const result = await api.rollback();
      setRollback(result);
      toast.info(
        result.result.restored
          ? `Restored ${result.result.restored_entities} entities`
          : "Nothing restored",
        { description: result.result.reason },
      );
      await refresh();
    } catch (err) {
      toast.error("Rollback failed", {
        description: err instanceof Error ? err.message : String(err),
      });
    } finally {
      setBusy(false);
    }
  };

  const run = async <T,>(id: BeatId, fn: () => Promise<T>, set: (v: T) => void) => {
    setLoadingBeat(id);
    try {
      set(await fn());
      await refresh();
    } catch (err) {
      toast.error("Beat failed", {
        description: err instanceof Error ? err.message : String(err),
      });
    } finally {
      setLoadingBeat(null);
    }
  };

  return (
    <div className="min-h-dvh">
      <EvidenceBar state={state} />

      <div className="mx-auto max-w-6xl px-6 py-8">
        {error && (
          <Alert variant="destructive" className="mb-6">
            <AlertTitle>Cannot reach the governance API</AlertTitle>
            <AlertDescription>
              {error}. Start it with <code className="hash">make demo</code>.
            </AlertDescription>
          </Alert>
        )}

        <div className="grid gap-8 lg:grid-cols-[190px_1fr] lg:gap-12">
          <BeatRail beats={beats} active={active} onSelect={setActive} />

          <main className="min-w-0">
            {!state && !error && (
              <div className="space-y-4">
                <Skeleton className="h-8 w-72" />
                <Skeleton className="h-40 w-full" />
                <Skeleton className="h-56 w-full" />
              </div>
            )}

            {active === "recall" && recall && <RecallPanel data={recall} />}
            {active === "chain" && state && <ChainPanel state={state} />}
            {active === "congress" && (
              <CongressPanel
                data={congress}
                loading={loadingBeat === "congress"}
                onRun={() => run("congress", api.congress, setCongress)}
              />
            )}
            {active === "heist" && state && (
              <HeistPanel
                cards={state.poison_cards}
                result={inject}
                rollback={rollback}
                busy={busy}
                onInject={onInject}
                onRollback={onRollback}
              />
            )}
            {active === "settlement" && (
              <SettlementPanel
                data={settlement}
                loading={loadingBeat === "settlement"}
                onRun={() => run("settlement", api.settlement, setSettlement)}
              />
            )}

            <footer className="mt-16 border-t border-border pt-5 text-[11px] text-muted-foreground">
              Governed coordination memory over{" "}
              <a
                href="https://docs.sibyllabs.org/memory/tiers"
                target="_blank"
                rel="noreferrer"
                className="underline underline-offset-4"
              >
                Sibyl Memory
              </a>{" "}
              · Sibyl Labs Hackathon 2026 ·{" "}
              <a
                href="https://github.com/Satianurag/ledgermind"
                target="_blank"
                rel="noreferrer"
                className="underline underline-offset-4"
              >
                source
              </a>
            </footer>
          </main>
        </div>
      </div>
    </div>
  );
}
