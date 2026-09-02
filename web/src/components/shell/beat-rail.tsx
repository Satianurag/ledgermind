"use client";

import { cn } from "@/lib/utils";

export type BeatId = "recall" | "heist" | "congress" | "settlement" | "chain";

export type Beat = {
  id: BeatId;
  index: string;
  title: string;
  caption: string;
  done: boolean;
};

/**
 * The demo has a sequence, so the UI shows one. Stacking five equal cards made every beat
 * look equally important and gave a viewer no idea where they were.
 */
export function BeatRail({
  beats,
  active,
  onSelect,
}: {
  beats: Beat[];
  active: BeatId;
  onSelect: (id: BeatId) => void;
}) {
  return (
    <nav className="flex gap-1.5 overflow-x-auto pb-1 lg:sticky lg:top-24 lg:flex-col lg:gap-1 lg:overflow-visible lg:pb-0">
      {beats.map((beat) => {
        const isActive = beat.id === active;
        return (
          <button
            key={beat.id}
            onClick={() => onSelect(beat.id)}
            aria-current={isActive ? "step" : undefined}
            className={cn(
              "group relative shrink-0 rounded-md border px-3 py-2.5 text-left transition-colors lg:w-full",
              isActive
                ? "border-border bg-card"
                : "border-transparent hover:border-border/60 hover:bg-card/50",
            )}
          >
            <span className="flex items-center gap-2.5">
              <span
                className={cn(
                  "hash tabular flex size-5 shrink-0 items-center justify-center rounded text-[10px]",
                  beat.done
                    ? "bg-verified-dim/25 text-verified"
                    : isActive
                      ? "bg-foreground text-background"
                      : "bg-muted text-muted-foreground",
                )}
              >
                {beat.done ? "✓" : beat.index}
              </span>
              <span
                className={cn(
                  "text-[13px] font-medium whitespace-nowrap",
                  isActive ? "text-foreground" : "text-muted-foreground",
                )}
              >
                {beat.title}
              </span>
            </span>
            <span className="mt-1 hidden pl-7.5 text-[11px] leading-snug text-muted-foreground lg:block">
              {beat.caption}
            </span>
          </button>
        );
      })}
    </nav>
  );
}
