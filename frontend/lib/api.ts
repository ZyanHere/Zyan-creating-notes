// Client for the plan gate. Five endpoints, no state of its own.
//
// The backend is synchronous: a turn is one or two model calls and takes
// 20-60s. Every caller has to hold a pending state for that long -- see
// `Plan-Gate-Milestone` §6. The job queue arrives at M4 with a reason.

const BASE = process.env.NEXT_PUBLIC_API ?? "http://127.0.0.1:8000";

export type Option = { label: string; implication: string };

export type Question = {
  axis: string;
  question: string;
  why_it_matters: string;
  options: Option[];
  default_label: string;
};

export type Situation = {
  subject: string;
  job: string;
  entry_point: string;
  purpose: string;
  target_capability: string;
  capacity: string | null;
  stated: string[];
  inferred: string[];
};

export type Covered = { concept: string; depth: string; why: string };
export type Exclusion = { topic: string; consequence: string; when_to_learn: string };
export type Unit = { heading: string; covers: string[]; why_here: string };

export type Decisions = {
  interpret_situation?: Situation;
  derive_structure?: { concepts: { name: string; built_from: string[] }[] };
  relevance?: { judgements: { concept: string; in_play: boolean; why: string }[] };
  scope?: { covered: Covered[]; cut: string[] };
  consequence?: { exclusions: Exclusion[] };
  partition?: { units: Unit[] };
  traversal?: { sequence: string[]; why: string };
  intake_strategy?: { questions: Question[] };
};

export type Turn = {
  correction: string;
  reading: string;
  claimed: string[];
  actual: string[];
  unchanged: string[];
  unclaimed_drift: string[];
  claimed_but_unchanged: string[];
  out_of_scope: string | null;
  not_understood: boolean;
};

export type AxisVerdict = {
  axis: string;
  value: string | null;
  strength: "stated" | "inferred" | "guessed" | "unknown";
  verified: { utterance_ord: number; quote: string }[];
  unverified: string[];
  material: boolean;
  would_differ: string | null;
  askable: boolean;
  asked: boolean;
  reason: string;
};

export type Sufficiency = {
  verdict: "needs_subject" | "ask" | "sufficient";
  budget: number;
  asking: string[];
  over_budget: string[];
  axes: AxisVerdict[];
};

export type Extent = {
  total?: string;
  pages?: string;
  study_time?: string;
  parts?: number;
  per_unit?: Record<string, string>;
};

export type Shortfall = {
  failure: string;
  concepts: string[];
  licenses: string;
  note: string;
};

export type Feasibility = {
  serves_everything?: boolean;
  shortfalls?: Shortfall[];
};

export type PlanView = {
  project_id: string;
  title: string;
  decisions: Decisions;
  questions: Question[];
  extent: Extent;
  feasibility: Feasibility;
  approved: boolean;
  state: "needs_subject" | "asking" | "planned";
  sufficiency: Sufficiency | Record<string, never>;
  transcript: { role: string; text: string }[];
  last_turn: Turn | null;
};

export type Commitment = {
  id: string;
  kind: string;
  approved_at: string;
  decision_ids: string[];
  snapshot: Record<string, unknown>;
};

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  listProjects: () =>
    call<{ id: string; title: string; created_at: string }[]>("/projects"),

  createProject: (text: string) =>
    call<PlanView>("/projects", { method: "POST", body: JSON.stringify({ text }) }),

  getPlan: (id: string) => call<PlanView>(`/projects/${id}/plan`),

  correct: (id: string, text: string) =>
    call<PlanView>(`/projects/${id}/utterances`, {
      method: "POST",
      body: JSON.stringify({ text }),
    }),

  // Plan now, on the defaults each open question carries. A question is an
  // offer to correct early, never a blocker.
  proceed: (id: string) =>
    call<PlanView>(`/projects/${id}/plan`, { method: "POST" }),

  approve: (id: string) =>
    call<Commitment>(`/projects/${id}/plan/approve`, {
      method: "POST",
      body: JSON.stringify({ decision_ids: [] }),
    }),
};
