"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { StateData } from "@/lib/api";
import { short } from "@/lib/api";

const TIER_ORDER = ["hot", "warm", "cold", "reference", "archive"];

function trustVariant(tier: string | null): "default" | "secondary" | "destructive" | "outline" {
  switch (tier) {
    case "trusted":
    case "internal":
      return "secondary";
    case "external":
    case "unknown":
      return "outline";
    case "hostile":
      return "destructive";
    default:
      return "outline";
  }
}

export function ChainPanel({ state }: { state: StateData }) {
  const brokenTrees = new Set(state.verification.broken.map((b) => b.tree));

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <CardTitle>Receipt chain</CardTitle>
            <CardDescription>
              Every governed write is provenance-stamped and hash-linked to its predecessor,
              inside Sibyl itself. No shadow store.
            </CardDescription>
          </div>
          <Badge variant={state.verification.all_ok ? "secondary" : "destructive"}>
            {state.verification.all_ok
              ? `${state.verification.trees} trees verified`
              : `${state.verification.broken.length} broken`}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap gap-2">
          {TIER_ORDER.filter((t) => state.tiers[t]).map((tier) => (
            <Badge key={tier} variant="outline" className="font-mono text-xs uppercase">
              {tier} · {state.tiers[tier]}
            </Badge>
          ))}
          <Badge variant="outline" className="text-xs">
            {state.entity_count} entities
          </Badge>
          {state.quarantined > 0 && (
            <Badge variant="destructive" className="text-xs">
              {state.quarantined} quarantined
            </Badge>
          )}
        </div>

        <ScrollArea className="h-[320px] rounded-md border">
          <Table>
            <TableHeader className="sticky top-0 bg-background">
              <TableRow>
                <TableHead className="w-[34%]">Tree</TableHead>
                <TableHead className="w-[8%]">Seq</TableHead>
                <TableHead className="w-[16%]">Agent</TableHead>
                <TableHead className="w-[14%]">Trust</TableHead>
                <TableHead>prev → hash</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {state.chain.map((link) => {
                const broken = brokenTrees.has(link.tree);
                return (
                  <TableRow
                    key={`${link.tree}-${link.sequence}`}
                    className={broken ? "bg-destructive/10" : undefined}
                  >
                    <TableCell className="font-mono text-xs">{link.tree}</TableCell>
                    <TableCell className="font-mono text-xs">{link.sequence}</TableCell>
                    <TableCell className="text-xs">{link.agent_id ?? "—"}</TableCell>
                    <TableCell>
                      <Badge variant={trustVariant(link.source_trust_tier)} className="text-[10px]">
                        {link.source_trust_tier ?? "—"}
                      </Badge>
                    </TableCell>
                    <TableCell className="font-mono text-[11px] text-muted-foreground">
                      {short(link.prev_hash, 8)} → <span className="text-foreground">{short(link.hash, 8)}</span>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
