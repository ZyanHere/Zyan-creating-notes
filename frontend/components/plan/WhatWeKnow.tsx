// The decider's record, shown to the user.
//
// Not debug output. Semantics §3 makes silence the system's decision, and a
// decision the user cannot see is one they cannot correct — this is that rule
// applied to the situation itself. An axis carried as an assumption because the
// question budget ran out is exactly the thing a user needs to be able to
// contradict, and it looks identical to a confident reading unless we say so.

import type { Sufficiency } from "@/lib/api";

const NAMES: Record<string, string> = {
  subject: "Subject",
  purpose: "Why you want it",
  entry_point: "What you already know",
  target_capability: "What you'll be able to do",
  capacity: "Time you have",
  depth_register: "Depth",
  artifact_type: "Kind of notes",
  template: "Look",
};

const TONE: Record<string, string> = {
  stated: "text-[color:var(--ink)]",
  inferred: "text-[color:var(--ink)]",
  guessed: "text-amber-800",
  unknown: "text-amber-800",
};

export function WhatWeKnow({ sufficiency }: { sufficiency: Sufficiency }) {
  const shown = sufficiency.axes.filter((a) => a.askable || a.value);
  if (shown.length === 0) return null;

  return (
    <details className="rounded-2xl border border-[color:var(--line)] bg-[color:var(--panel-soft)] p-5">
      <summary className="cursor-pointer text-sm font-medium text-[color:var(--ink)]">
        What this rests on, and why we did or didn&apos;t ask
      </summary>

      <ul className="mt-4 space-y-3">
        {shown.map((a) => (
          <li key={a.axis} className="border-t border-[color:var(--line)] pt-3 first:border-t-0 first:pt-0">
            <div className="flex flex-wrap items-baseline gap-2">
              <span className="text-sm font-medium text-[color:var(--ink)]">
                {NAMES[a.axis] ?? a.axis}
              </span>
              <span className={`text-xs uppercase tracking-wider ${TONE[a.strength]}`}>
                {a.strength}
              </span>
              {a.asked && (
                <span className="rounded-full bg-[color:var(--ink)] px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-white">
                  asked
                </span>
              )}
            </div>
            {a.value && (
              <p className="mt-1 text-sm leading-6 text-[color:var(--ink)]">{a.value}</p>
            )}
            <p className="mt-1 text-xs leading-5 text-[color:var(--muted)]">{a.reason}</p>
            {a.would_differ && a.strength !== "stated" && (
              <p className="mt-1 text-xs leading-5 text-[color:var(--muted)]">
                If wrong: {a.would_differ}
              </p>
            )}
          </li>
        ))}
      </ul>

      {sufficiency.over_budget.length > 0 && (
        <p className="mt-4 text-xs leading-5 text-amber-800">
          {sufficiency.over_budget.length} more would have been worth asking about,
          but we only spend {sufficiency.budget} question
          {sufficiency.budget === 1 ? "" : "s"} before planning. They&apos;re
          assumptions above — contradict any of them.
        </p>
      )}
    </details>
  );
}
