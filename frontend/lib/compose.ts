// Decision records → the document the user reads.
//
// The page's job is to answer one question: "is this the document I want?" A
// contents page answers that; a list of six decision records does not. So this
// module composes the records into a narrative and the components render the
// narrative — nothing named `scope`, `partition`, `traversal` or `consequence`
// reaches the screen.
//
// Pure functions, no JSX, so the composition is testable on its own. The
// records themselves are untouched and stay available under "How this was
// decided".

import type { Decisions, Extent, Feasibility, Shortfall, Sufficiency } from "@/lib/api";

// The model writes `mention | explain | work through`. Those are fine words for
// a schema and slightly wrong ones for a reader.
const DEPTH_WORDS: Record<string, string> = {
  mention: "briefly",
  explain: "explained",
  "work through": "worked through",
};

export const depthWord = (depth: string) =>
  DEPTH_WORDS[depth.trim().toLowerCase()] ?? depth;

// Reader-facing names for the decisions, shared by the turn report and the
// provenance panel so one vocabulary is used wherever a decision is named.
export const DECISION_NAMES: Record<string, string> = {
  interpret_situation: "who this is for",
  derive_structure: "the concepts we considered",
  relevance: "what's relevant to you",
  scope: "what's covered",
  consequence: "what's left out",
  partition: "the parts",
  traversal: "the order",
  intake_strategy: "what to ask you",
};

export const AXIS_NAMES: Record<string, string> = {
  subject: "Subject",
  purpose: "Why you want it",
  entry_point: "What you already know",
  target_capability: "What you'll be able to do",
  capacity: "Time you have",
  depth_register: "Depth",
  artifact_type: "Kind of notes",
  template: "Look",
};

export const decisionName = (kind: string) => DECISION_NAMES[kind] ?? kind;
export const axisName = (axis: string) => AXIS_NAMES[axis] ?? axis;

export type ContentItem = { concept: string; depth: string; why: string };

export type ContentUnit = {
  heading: string;
  why: string;
  extent: string | null;
  items: ContentItem[];
  /** What the learner can do after this module, on its own. Only modules have
   *  one — it is the test that separates a module from a chapter. Null for a
   *  legacy plan's sections, which never had one. */
  capability: string | null;
};

export type Omission = { topic: string; consequence: string; whenToLearn: string };

export type Assumption = { text: string; detail: string | null };

export type CannotDo = { what: string; concepts: string[]; why: string };

// Reader-facing names for the prose failures. The taxonomy is Architecture
// §13's and stays domain-free; only the phrasing changes here.
const FAILURE_NAMES: Record<string, string> = {
  "perceptual-referent": "Pictures of the things themselves",
  "parallel-state": "Timelines and side-by-side sequences",
  topology: "Relationship diagrams",
  "cross-reference": "Comparison tables",
};

export const failureName = (f: string) => FAILURE_NAMES[f] ?? f;

export type PlanDoc = {
  title: string;
  subtitle: string | null;
  meta: string[];
  writtenFor: string | null;
  byTheEnd: string | null;
  capacity: string | null;
  stated: string[];
  orderNote: string | null;
  contents: ContentUnit[];
  /** Several modules, so several PDFs — the page frames itself differently. */
  isCurriculum: boolean;
  moduleCount: number;
  wontCover: Omission[];
  assumptions: Assumption[];
  cannotDo: CannotDo[];
  ready: boolean;
};

export function compose(
  decisions: Decisions,
  extent: Extent,
  feasibility: Feasibility,
  sufficiency: Sufficiency | null,
  fallbackTitle: string,
): PlanDoc {
  const s = decisions.interpret_situation;
  const covered = decisions.scope?.covered ?? [];

  // Modules are the curriculum's parts — each becomes its own PDF. `units` is
  // the legacy shape: sections of a single document, from before the curriculum
  // layer existed. Read so old projects still open; never relabelled modules.
  const modules = decisions.partition?.modules ?? [];
  const legacy = decisions.partition?.units ?? [];
  const parts = modules.length
    ? modules.map((m) => ({
        heading: m.title,
        why: m.why_here,
        covers: m.covers,
        capability: m.capability as string | null,
      }))
    : legacy.map((u) => ({
        heading: u.heading,
        why: u.why_here,
        covers: u.covers,
        capability: null,
      }));

  // Traversal owns the order; partition owns the grouping. The reader sees one
  // list, which is both.
  const ordered = decisions.traversal?.sequence?.length
    ? decisions.traversal.sequence
    : parts.map((p) => p.heading);
  const byHeading = new Map(parts.map((p) => [p.heading, p]));
  const byConcept = new Map(covered.map((c) => [c.concept, c]));

  const contents: ContentUnit[] = ordered
    .map((heading) => {
      const part = byHeading.get(heading);
      if (!part) return null;
      return {
        heading,
        why: part.why,
        capability: part.capability,
        extent: extent?.per_unit?.[heading] ?? null,
        items: part.covers
          .map((name) => byConcept.get(name))
          .filter((c): c is ContentItem => Boolean(c)),
      };
    })
    .filter((u): u is ContentUnit => u !== null);

  // A concept that is covered but landed in no unit would silently vanish from
  // the contents. Surface it rather than lose it.
  const placed = new Set(contents.flatMap((u) => u.items.map((i) => i.concept)));
  const orphans = covered.filter((c) => !placed.has(c.concept));
  if (orphans.length > 0) {
    contents.push({
      heading: "Also covered",
      why: "Not yet grouped into a part.",
      capability: null,
      extent: null,
      items: orphans,
    });
  }

  // Deduped here as well as in the plan contract, because plans approved before
  // that validator existed are still on disk and still render. `topic` is the
  // list's React key, so a repeat is a duplicate-key warning as well as a
  // paragraph the reader is shown twice.
  const seenExclusions = new Set<string>();
  const wontCover: Omission[] = (decisions.consequence?.exclusions ?? [])
    .filter((e) => {
      const key = e.topic.trim().toLowerCase();
      if (seenExclusions.has(key)) return false;
      seenExclusions.add(key);
      return true;
    })
    .map((e) => ({
      topic: e.topic,
      consequence: e.consequence,
      whenToLearn: e.when_to_learn,
    }));

  // Two sources of "we decided this for you": what the model recorded as
  // inferred, and axes the decider judged worth asking about but could not fit
  // in the question budget. The second kind is the one a user most needs to
  // see, so it carries its consequence.
  const assumptions: Assumption[] = (s?.inferred ?? []).map((text) => ({
    text,
    detail: null,
  }));
  for (const axis of sufficiency?.axes ?? []) {
    if (!sufficiency?.over_budget.includes(axis.axis)) continue;
    assumptions.push({
      text: `${axisName(axis.axis)}: ${axis.value ?? "assumed a default"}`,
      detail: axis.would_differ ? `If that's wrong — ${axis.would_differ}` : null,
    });
  }

  // Not the same as "what this won't cover": those are choices, these are
  // limits. Architecture §13 requires the limitation be reported rather than
  // answered with prose that leaves out what carried the meaning.
  const cannotDo: CannotDo[] = (feasibility?.shortfalls ?? []).map((s: Shortfall) => ({
    what: failureName(s.failure),
    concepts: s.concepts,
    why: s.note,
  }));

  // A curriculum's headline is how many documents it is, because that is the
  // thing the reader is about to receive. One module is a document, not a
  // curriculum of one, and reads as it always did.
  const moduleCount = modules.length;
  const isCurriculum = moduleCount > 1;

  const meta: string[] = [];
  if (isCurriculum) meta.push(`${moduleCount} modules · ${moduleCount} PDFs`);
  if (extent?.pages) meta.push(extent.pages);
  if (extent?.study_time) meta.push(extent.study_time);
  if (!isCurriculum && contents.length > 1) {
    meta.push(`${contents.length} parts`);
  }

  return {
    title: s?.subject ?? fallbackTitle,
    subtitle: s?.purpose ?? null,
    meta,
    writtenFor: s?.entry_point ?? null,
    byTheEnd: s?.target_capability ?? null,
    capacity: s?.capacity ?? null,
    // Objects since constraints gained axis attribution; legacy plans hold
    // bare strings. The reader only ever wanted the words.
    stated: (s?.stated ?? []).map((c) => (typeof c === "string" ? c : c.text)),
    orderNote: decisions.traversal?.why ?? null,
    contents,
    isCurriculum,
    moduleCount,
    wontCover,
    assumptions,
    cannotDo,
    ready: Boolean(decisions.scope && decisions.partition),
  };
}
