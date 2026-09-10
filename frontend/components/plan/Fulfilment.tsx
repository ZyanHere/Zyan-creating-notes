"use client";

// Did you get the document you approved?
//
// The plan gate promises "what gets written is what you just read". This is
// where that promise is either kept or shown not to be — a run once produced one
// of six approved parts, omitted fifteen of seventeen concepts, and reported
// success in green. The check exists so that cannot happen quietly; this
// component exists so it cannot happen invisibly.
//
// Deliberately not a debug panel. It answers one question in the reader's terms:
// is this the document that was agreed?

import type { Fulfilment } from "@/lib/api";

export function FulfilmentReport({ report }: { report: Fulfilment }) {
  const ok = report.satisfied;
  const pct = Math.round(report.coverage * 100);

  return (
    <section className={`note mt-5 ${ok ? "note-ok" : "note-warn"}`}>
      <p className="eyebrow" style={{ color: "inherit" }}>
        {ok ? "Matches your approved plan" : "Does not match your approved plan"}
      </p>

      <p className="mt-2 text-sm leading-6">
        {report.units_generated.length} of {report.units_approved.length} parts written ·{" "}
        {report.concepts_covered.length} of {report.concepts_required.length} topics
        covered ({pct}%)
      </p>

      {!ok && (
        <ul className="mt-3 space-y-1.5">
          {report.problems.map((problem) => (
            <li key={problem} className="text-sm leading-6">
              — {problem}
            </li>
          ))}
        </ul>
      )}

      <details className="mt-3">
        <summary className="cursor-pointer text-sm text-[color:var(--muted)] transition-colors hover:text-[color:var(--accent)]">
          Part by part
        </summary>
        <table className="mt-3 w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-wider text-[color:var(--muted)]">
              <th className="pb-1.5 pr-3 font-medium">Part</th>
              <th className="pb-1.5 pr-3 font-medium">Topics</th>
              <th className="pb-1.5 font-medium">Missing</th>
            </tr>
          </thead>
          <tbody>
            {report.units.map((unit) => (
              <tr key={unit.heading} className="border-t border-[color:var(--line)]/60 align-top">
                <td className="py-1.5 pr-3">
                  {unit.heading}
                  {!unit.generated && (
                    <span className="ml-2 font-[family-name:var(--font-mono)] text-[0.6875rem] text-[color:var(--warn-ink)]">
                      not written
                    </span>
                  )}
                </td>
                <td className="py-1.5 pr-3 tabular-nums text-[color:var(--muted)]">
                  {unit.concepts_covered.length}/{unit.concepts_required.length}
                </td>
                <td className="py-1.5 text-[color:var(--soft)]">
                  {unit.concepts_missing.join(", ") || "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>

      {/* The check is completeness, not quality. Saying so is the difference
          between a check and a claim -- and how a treatment is best taught is a
          question the system has not answered yet. */}
      <p className="mt-3 text-xs leading-5 text-[color:var(--muted)]">
        &ldquo;Covered&rdquo; means the topic appears in the part it was planned
        for. It doesn&apos;t judge how well it was taught.
      </p>
    </section>
  );
}
