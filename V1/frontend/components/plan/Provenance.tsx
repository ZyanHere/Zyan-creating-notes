// Everything the system used and the reader does not need.
//
// Available, never mandatory. The decision records are the system's account of
// itself — which prose-failure fired on which node, what supported each reading
// of the situation, why a question was or was not asked. A user answering "is
// this the document I want?" needs none of it; a user asking "why did you
// decide that?" needs all of it.

import type { Decisions, Sufficiency } from "@/lib/api";
import { axisName, decisionName } from "@/lib/compose";

const STRENGTH_TONE: Record<string, string> = {
  stated: "text-[color:var(--ink)]",
  inferred: "text-[color:var(--ink)]",
  guessed: "text-[color:var(--warn-ink)]",
  unknown: "text-[color:var(--warn-ink)]",
};

export function Provenance({
  decisions,
  sufficiency,
}: {
  decisions: Decisions;
  sufficiency: Sufficiency | null;
}) {
  const concepts = decisions.derive_structure?.concepts ?? [];
  const judgements = decisions.relevance?.judgements ?? [];
  const dropped = judgements.filter((j) => !j.in_play);

  return (
    <details className="mt-10 border-t border-[color:var(--line)] pt-5">
      <summary className="group inline-flex cursor-pointer items-center gap-2 text-sm text-[color:var(--muted)] transition-colors hover:text-[color:var(--accent)]">
        <span
          aria-hidden
          className="text-[0.625rem] transition-transform group-open:rotate-90"
        >
          ▶
        </span>
        Provenance
      </summary>

      <div className="mt-5 space-y-7">
        {sufficiency && (
          <section>
            <h3 className="eyebrow">
              What we knew about you, and why we did or didn&apos;t ask
            </h3>
            <ul className="mt-3 space-y-2.5">
              {sufficiency.axes
                .filter((a) => a.askable || a.value)
                .map((a) => (
                  <li key={a.axis} className="text-sm leading-6">
                    <span className="text-[color:var(--ink)]">{axisName(a.axis)}</span>{" "}
                    <span
                      className={`rounded border border-[color:var(--line)] px-1.5 py-0.5 font-[family-name:var(--font-mono)] text-[0.625rem] uppercase tracking-wider ${STRENGTH_TONE[a.strength]}`}
                    >
                      {a.strength}
                    </span>
                    {a.asked && (
                      <span className="ml-1.5 rounded border border-[color:var(--accent-line)] bg-[color:var(--accent-bg)] px-1.5 py-0.5 font-[family-name:var(--font-mono)] text-[0.625rem] uppercase tracking-wider text-[color:var(--accent)]">
                        asked
                      </span>
                    )}
                    <span className="block text-xs leading-5 text-[color:var(--muted)]">
                      {a.reason}
                    </span>
                  </li>
                ))}
            </ul>
            <p className="mt-3 text-xs text-[color:var(--muted)]">
              Question budget: {sufficiency.budget}
            </p>
          </section>
        )}

        {concepts.length > 0 && (
          <section>
            <h3 className="eyebrow">
              Everything we considered ({concepts.length})
            </h3>
            <p className="mt-2 text-sm leading-6 text-[color:var(--muted)]">
              {concepts.map((c) => c.name).join(" · ")}
            </p>
          </section>
        )}

        {dropped.length > 0 && (
          <section>
            <h3 className="eyebrow">
              Considered and left out ({dropped.length})
            </h3>
            <ul className="mt-3 space-y-2">
              {dropped.map((j) => (
                <li key={j.concept} className="text-sm leading-6">
                  <span className="text-[color:var(--ink)]">{j.concept}</span>
                  <span className="block text-xs leading-5 text-[color:var(--muted)]">{j.why}</span>
                </li>
              ))}
            </ul>
          </section>
        )}

        <section>
          <h3 className="eyebrow">
            Decisions on record
          </h3>
          <p className="mt-2 text-sm leading-6 text-[color:var(--muted)]">
            {Object.keys(decisions).map(decisionName).join(" · ")}
          </p>
        </section>
      </div>
    </details>
  );
}
