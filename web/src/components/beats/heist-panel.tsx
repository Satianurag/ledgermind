"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import type { InjectData, RollbackData, StateData } from "@/lib/api";

const PATH_LABEL: Record<string, string> = {
  "source-trust": "Source trust",
  "chain-integrity": "Chain integrity",
  "content-heuristic": "Content heuristic (advisory)",
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
    <Card>
      <CardHeader>
        <CardTitle>The heist</CardTitle>
        <CardDescription>
          Inject a poisoned fact into shared memory and see which defense paths fire. Each is
          reported as what it actually is — a content keyword match is never labelled a chain break.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap gap-2">
          {cards.map((card) => (
            <Button
              key={card.id}
              size="sm"
              variant="outline"
              disabled={busy}
              onClick={() => onInject(card.id)}
              title={card.text}
            >
              {card.label}
              <Badge variant="secondary" className="ml-2 text-[10px]">
                {card.tier}
              </Badge>
            </Button>
          ))}
        </div>

        {result && (
          <>
            <Separator />
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant={result.verdict.caught ? "secondary" : "destructive"}>
                  {result.verdict.caught ? "CAUGHT" : "NOT CAUGHT"}
                </Badge>
                {result.verdict.paths_fired.map((path) => (
                  <Badge key={path} variant="outline" className="text-[10px]">
                    {PATH_LABEL[path] ?? path}
                  </Badge>
                ))}
              </div>
              <blockquote className="border-l-2 pl-3 text-sm italic text-muted-foreground">
                “{result.card.text}”
              </blockquote>
              <p className="text-xs text-muted-foreground">{result.verdict.detail}</p>
            </div>
          </>
        )}

        <Separator />
        <div className="flex flex-wrap items-center gap-3">
          <Button size="sm" variant="secondary" onClick={onRollback} disabled={busy}>
            Roll back to checkpoint
          </Button>
          {rollback && (
            <span className="text-xs text-muted-foreground">
              {rollback.result.restored
                ? `restored ${rollback.result.restored_entities} entities`
                : rollback.result.reason}
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
