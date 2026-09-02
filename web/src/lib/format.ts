/** Presentation helpers. Colour is semantic — see globals.css. */

export type Semantic = "verified" | "caution" | "breach" | "evidence" | "neutral";

/**
 * A 64-character hash is unreadable inline and unverifiable when truncated to one end.
 * Showing both ends keeps it comparable against an explorer at a glance.
 */
export function hash(value: string | null | undefined, head = 8, tail = 6): string {
  if (!value) return "—";
  const raw = value.startsWith("0x") ? value.slice(2) : value;
  const prefix = value.startsWith("0x") ? "0x" : "";
  if (raw.length <= head + tail + 1) return value;
  return `${prefix}${raw.slice(0, head)}⋯${raw.slice(-tail)}`;
}

/** Trust tiers map to one meaning each, everywhere in the app. */
export function trustSemantic(tier: string | null | undefined): Semantic {
  switch (tier) {
    case "trusted":
    case "internal":
    case "verified":
      return "verified";
    case "external":
      return "caution";
    case "unknown":
      return "caution";
    case "hostile":
      return "breach";
    default:
      return "neutral";
  }
}

export const SEMANTIC_TEXT: Record<Semantic, string> = {
  verified: "text-verified",
  caution: "text-caution",
  breach: "text-breach",
  evidence: "text-evidence",
  neutral: "text-muted-foreground",
};

export const SEMANTIC_DOT: Record<Semantic, string> = {
  verified: "bg-verified",
  caution: "bg-caution",
  breach: "bg-breach",
  evidence: "bg-evidence",
  neutral: "bg-muted-foreground",
};

export const SEMANTIC_CHIP: Record<Semantic, string> = {
  verified: "border-verified-dim/60 bg-verified-dim/15 text-verified",
  caution: "border-caution-dim/60 bg-caution-dim/15 text-caution",
  breach: "border-breach-dim/60 bg-breach-dim/15 text-breach",
  evidence: "border-evidence-dim/60 bg-evidence-dim/15 text-evidence",
  neutral: "border-border bg-muted/40 text-muted-foreground",
};

export const TIER_LABEL: Record<string, string> = {
  hot: "HOT",
  warm: "WARM",
  cold: "COLD",
  reference: "REFERENCE",
  archive: "ARCHIVE",
};
