import { cn } from "@/lib/utils";
import { SEMANTIC_CHIP, SEMANTIC_DOT, type Semantic } from "@/lib/format";

/** One chip primitive so state reads identically everywhere in the console. */
export function Chip({
  children,
  tone = "neutral",
  dot = false,
  mono = false,
  className,
}: {
  children: React.ReactNode;
  tone?: Semantic;
  dot?: boolean;
  mono?: boolean;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[11px] leading-none",
        SEMANTIC_CHIP[tone],
        mono && "hash",
        className,
      )}
    >
      {dot && <span className={cn("size-1.5 rounded-full", SEMANTIC_DOT[tone])} />}
      {children}
    </span>
  );
}

/** Small uppercase label. Used to title every field so nothing floats unlabelled. */
export function Label({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <span
      className={cn(
        "text-[10px] font-medium uppercase tracking-[0.12em] text-muted-foreground",
        className,
      )}
    >
      {children}
    </span>
  );
}
