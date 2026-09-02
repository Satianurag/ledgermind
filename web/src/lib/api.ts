/** Typed client for the Ledgermind FastAPI backend. */

const BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8787";

export type ChainLink = {
  tree: string;
  sequence: number;
  prev_hash: string;
  hash: string;
  agent_id: string | null;
  timestamp: string | null;
  source_trust_tier: string | null;
  evidence_ref: string | null;
};

export type PoisonCard = {
  id: string;
  label: string;
  tier: string;
  text: string;
  simulate_chain_break?: boolean;
};

export type StateData = {
  commit: string;
  timestamp: string;
  chain: ChainLink[];
  chain_length: number;
  tiers: Record<string, number>;
  entity_count: number;
  quarantined: number;
  verification: {
    trees: number;
    all_ok: boolean;
    broken: Array<{ tree: string; broken_sequence: number | null; message: string }>;
  };
  poison_cards: PoisonCard[];
};

export type Verdict = {
  caught: boolean;
  paths_fired: string[];
  quarantined: boolean;
  chain_break: boolean;
  content_flag: boolean;
  detail: string;
};

export type InjectData = { card: PoisonCard; verdict: Verdict; timestamp: string };

export type RollbackData = {
  result: {
    label: string;
    restored: boolean;
    restored_entities: number;
    reason?: string;
    chain_head?: string;
  };
};

export type Claimant = {
  agent_id: string;
  content_hash: string;
  content: Record<string, unknown>;
};

export type CongressData = {
  dispute: {
    dispute_id: string;
    subject: { category: string; name: string };
    claimants: Claimant[];
    status: string;
    confidence: number;
    resolution: {
      winner_agent: string;
      winner_hash: string;
      arbiter_backend: string;
      arbiter_reasoning: string;
      citations: Array<{ tree: string }>;
    } | null;
    receipt_sig: string | null;
  };
  arbiter: Record<string, unknown>;
};

export type Receipt = {
  kind: string;
  tx_hash?: string;
  explorer_url?: string;
  amount_usdc?: number;
  network?: string;
  source?: string;
  token?: string;
};

export type SettlementData = {
  receipts: Receipt[];
  unexercised_stacks: string[];
  bootstrap_hint: string | null;
  decision: string;
  why: string;
  counterparty: Record<string, unknown>;
  counterparty_hash: string | null;
  cap_check_over?: { allowed: boolean; reason?: string; policy_key?: string };
  cap_check_under?: { allowed: boolean; effective_cap_usdc?: number };
  flip: {
    baseline: string;
    counterfactual: string;
    flipped: boolean;
    removed_key: string;
    removed_content_hash: string | null;
    explanation: string;
  };
  entry: { decision_id: string; citations: Array<{ key: string; content_hash: string }> };
};

export type RecallData = {
  commit: string;
  timestamp: string;
  priority: Record<string, unknown> | null;
  counterparty: Record<string, unknown> | null;
  counterparty_hash: string | null;
  policy: Record<string, unknown> | null;
  events: number;
  decision: string;
  why: string;
  counterfactual: SettlementData["flip"];
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    cache: "no-store",
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!res.ok) {
    throw new Error(`${path} returned ${res.status}`);
  }
  return (await res.json()) as T;
}

export const api = {
  state: () => request<StateData>("/api/state"),
  recall: () => request<RecallData>("/api/recall"),
  congress: () => request<CongressData>("/api/congress"),
  settlement: () => request<SettlementData>("/api/settlement"),
  inject: (card_id: string, text = "") =>
    request<InjectData>("/api/inject", {
      method: "POST",
      body: JSON.stringify({ card_id, text }),
    }),
  rollback: () => request<RollbackData>("/api/rollback", { method: "POST" }),
};

export function short(hash: string | null | undefined, len = 10): string {
  if (!hash) return "—";
  return hash.length <= len ? hash : `${hash.slice(0, len)}…`;
}
