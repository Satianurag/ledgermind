"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { ChainPanel } from "@/components/beats/chain-panel";
import { CongressPanel } from "@/components/beats/congress-panel";
import { HeistPanel } from "@/components/beats/heist-panel";
import { RecallPanel } from "@/components/beats/recall-panel";
import { SettlementPanel } from "@/components/beats/settlement-panel";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
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
  const [loadingBeat, setLoadingBeat] = useState<string | null>(null);

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

  // Client-side load of live governance state. The abort guard keeps a slow response from
  // writing into an unmounted tree during the demo's rapid beat switching.
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

  const run = async <T,>(name: string, fn: () => Promise<T>, set: (v: T) => void) => {
    setLoadingBeat(name);
    try {
      set(await fn());
      await refresh();
    } catch (err) {
      toast.error(`${name} failed`, {
        description: err instanceof Error ? err.message : String(err),
      });
    } finally {
      setLoadingBeat(null);
    }
  };

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

  return (
    <main className="mx-auto max-w-5xl space-y-6 px-4 py-10">
      <header className="space-y-2">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-semibold tracking-tight">Ledgermind</h1>
          {state && (
            <>
              <Badge variant="outline" className="font-mono text-xs">
                {state.commit}
              </Badge>
              <Badge variant="outline" className="font-mono text-xs">
                {state.timestamp}
              </Badge>
            </>
          )}
        </div>
        <p className="max-w-2xl text-sm text-muted-foreground">
          Governed coordination memory for agent teams. Every read and write crosses one
          governance boundary into Sibyl — provenance-stamped, hash-linked, and adjudicated
          instead of overwritten.
        </p>
      </header>

      {error && (
        <Alert variant="destructive">
          <AlertTitle>Cannot reach the governance API</AlertTitle>
          <AlertDescription>
            {error}. Start it with <code>make ui</code> (FastAPI on :8787).
          </AlertDescription>
        </Alert>
      )}

      {!state && !error && (
        <div className="space-y-4">
          <Skeleton className="h-40 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      )}

      {recall && <RecallPanel data={recall} />}
      {state && <ChainPanel state={state} />}
      {state && (
        <HeistPanel
          cards={state.poison_cards}
          result={inject}
          rollback={rollback}
          busy={busy}
          onInject={onInject}
          onRollback={onRollback}
        />
      )}
      <CongressPanel
        data={congress}
        loading={loadingBeat === "congress"}
        onRun={() => run("congress", api.congress, setCongress)}
      />
      <SettlementPanel
        data={settlement}
        loading={loadingBeat === "settlement"}
        onRun={() => run("settlement", api.settlement, setSettlement)}
      />

      <footer className="pt-4 text-xs text-muted-foreground">
        Sibyl Labs Hackathon · Sep 2026 ·{" "}
        <a
          className="underline underline-offset-2"
          href="https://github.com/Satianurag/ledgermind"
          target="_blank"
          rel="noreferrer"
        >
          source
        </a>
      </footer>
    </main>
  );
}
