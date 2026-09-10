// Client for the plan gate and the generation that follows it.
//
// Two timing shapes, deliberately different. Plan turns are synchronous: one or
// two model calls, 20-60s, and the caller holds a pending state. Generation is
// not -- it is minutes long and has returned empty, so it starts and is polled.
// See `backend/jobs.py` for why that is a thread and not a queue.

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
  /** What the user actually said, with the axis it constrains (null if none).
   *  Legacy plans stored bare strings. */
  stated: (string | { text: string; axis: string | null })[];
  inferred: string[];
};

export type Covered = { concept: string; depth: string; why: string };
export type Exclusion = { topic: string; consequence: string; when_to_learn: string };
/** A module of the curriculum. Becomes its own PDF. */
export type Module = {
  title: string;
  covers: string[];
  why_here: string;
  capability: string;
};

/** LEGACY: a section of a single document, from before the curriculum layer. */
export type Unit = { heading: string; covers: string[]; why_here: string };

export type Decisions = {
  interpret_situation?: Situation;
  derive_structure?: { concepts: { name: string; built_from: string[] }[] };
  relevance?: { judgements: { concept: string; in_play: boolean; why: string }[] };
  scope?: { covered: Covered[]; cut: string[] };
  consequence?: { exclusions: Exclusion[] };
  partition?: { modules?: Module[]; units?: Unit[] };
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

export type UnitReport = {
  heading: string;
  generated: boolean;
  satisfied: boolean;
  concepts_required: string[];
  concepts_covered: string[];
  concepts_missing: string[];
  // Observation only, never a requirement: the treatment taxonomy has not
  // had its design pass, so nothing here decides `satisfied`.
  treatments_anticipated: string[];
  treatments_produced: string[];
  depths_required: string[];
  blocks: number;
  words: number;
  notes: string[];
};

export type Fulfilment = {
  satisfied: boolean;
  coverage: number;
  units_approved: string[];
  units_generated: string[];
  units_missing: string[];
  concepts_required: string[];
  concepts_covered: string[];
  concepts_missing: string[];
  changed: string[];
  problems: string[];
  units: UnitReport[];
};

export type Generation = {
  state: "idle" | "running" | "done" | "failed";
  // Whether the artifact delivers the approved plan. Separate from `state`:
  // the job can finish cleanly and still not have produced what was agreed,
  // and collapsing the two is how an incomplete document reported success.
  satisfied?: boolean;
  fulfilment?: Fulfilment | null;
  calls?: number;
  seconds?: number;
  error?: string | null;
  pdf?: string;
  title?: string;
  pages?: number;
  provider?: string;
  model?: string;
  repairs?: number;
  representation?: {
    stated_gaps: string[];
    unrendered: string[];
    undiagnosed: number;
    scale: number;
  };
};

// Inline by default so it renders in the page; `download` sets the attachment
// disposition for an explicit save.
export type ModuleState = {
  index: number;
  title: string;
  capability: string;
  why_here: string;
  concepts: string[];
  /** Each concept with the depth it was approved at, read from the *committed*
   *  snapshot rather than from current decisions — so the generation screen
   *  shows the promise that was actually made. Absent on legacy snapshots. */
  coverage?: { concept: string; depth: string; why: string }[];
  extent: string | null;
  state: "idle" | "running" | "done" | "failed";
  seconds?: number;
  error?: string | null;
  pdf?: string;
  pages?: number;
  calls?: number;
  satisfied?: boolean;
  fulfilment?: Fulfilment | null;
  representation?: { stated_gaps: string[]; unrendered: string[] };
};

/** One row of the project index.
 *
 *  `title` is derived server-side from the plan's subject and falls back to the
 *  raw query; `query` is always the opening request. Two fields rather than one
 *  because the derived title is what tells two projects apart, and the query is
 *  what the user recognises as theirs. */
export type ProjectSummary = {
  id: string;
  title: string;
  query: string;
  created_at: string;
  state: "unread" | "needs_subject" | "asking" | "ready" | "planned";
  approved: boolean;
  modules_done: number;
  modules_total: number;
};

export const projectExportUrl = (id: string) => `${BASE}/projects/${id}/export.zip`;

export const moduleArtifactUrl = (id: string, index: number, download = false) =>
  `${BASE}/projects/${id}/modules/${index}/artifact.pdf${download ? "?download=1" : ""}`;

export const artifactUrl = (id: string, download = false) =>
  `${BASE}/projects/${id}/artifact.pdf${download ? "?download=1" : ""}`;

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
  listProjects: () => call<ProjectSummary[]>("/projects"),

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

  // Refused without an approved plan, by design: generating from an unapproved
  // plan is the failure the gate exists to prevent.
  // Modules are the unit of generation. One at a time, on demand -- never a
  // batch over the curriculum.
  listModules: (id: string) =>
    call<{ modules: ModuleState[] }>(`/projects/${id}/modules`),

  generateModule: (id: string, index: number) =>
    call<{ state: string; index: number }>(
      `/projects/${id}/modules/${index}/generate`,
      { method: "POST" },
    ),
};
