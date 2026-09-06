// What the last correction did, shown before the revised plan.
//
// "Deferred" is not an error state: it is the system correctly declining a
// well-formed request that belongs to a gate which does not exist yet, and it
// has to read that way. Drift is surfaced, never repaired.

import type { Turn } from "@/lib/api";

const NAMES: Record<string, string> = {
  interpret_situation: "what we read your request as",
  derive_structure: "what concepts exist",
  relevance: "what's in play for you",
  scope: "what's covered",
  consequence: "what's left out",
  partition: "the units",
  traversal: "the order",
  intake_strategy: "what to ask next",
};

const name = (k: string) => NAMES[k] ?? k;

export function TurnReport({ turn }: { turn: Turn }) {
  return (
    <div className="rounded-2xl border border-[color:var(--line)] bg-[color:var(--panel-strong)] p-5">
      <p className="text-sm leading-6 text-[color:var(--ink)]">
        <span className="text-[color:var(--muted)]">Read as: </span>
        {turn.reading}
      </p>

      {turn.out_of_scope && (
        <p className="mt-3 rounded-xl border border-sky-200 bg-sky-50 p-3 text-sm leading-6 text-sky-900">
          Not a plan decision — {turn.out_of_scope} Nothing in the plan changed.
        </p>
      )}

      {turn.not_understood && (
        <p className="mt-3 rounded-xl border border-amber-300 bg-amber-50 p-3 text-sm leading-6 text-amber-900">
          That didn&apos;t land anywhere. Try saying it a different way — name what
          feels wrong about the plan.
        </p>
      )}

      {turn.actual.length > 0 && (
        <p className="mt-3 text-sm leading-6 text-[color:var(--ink)]">
          <span className="text-[color:var(--muted)]">Changed: </span>
          {turn.actual.map(name).join(", ")}
        </p>
      )}

      {turn.actual.length > 0 && (
        <p className="mt-1 text-sm leading-6 text-[color:var(--muted)]">
          Untouched: {turn.unchanged.map(name).join(", ")}
        </p>
      )}

      {/* Reported, never repaired. */}
      {turn.unclaimed_drift.length > 0 && (
        <p className="mt-3 text-xs leading-5 text-amber-800">
          Also moved without being asked to:{" "}
          {turn.unclaimed_drift.map(name).join(", ")}
        </p>
      )}
      {turn.claimed_but_unchanged.length > 0 && (
        <p className="mt-1 text-xs leading-5 text-amber-800">
          Said it would change but didn&apos;t:{" "}
          {turn.claimed_but_unchanged.map(name).join(", ")}
        </p>
      )}
    </div>
  );
}
