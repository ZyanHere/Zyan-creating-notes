// The fine print of what was approved: what it won't cover, what we can't
// produce for this subject, and what we decided for you.
//
// Extracted so it has exactly one implementation and two homes. Before
// approval it is the tail of the plan document, read in order. After approval
// the plan document is gone — its contents now live on the module cards, which
// is where they are actually acted on — but these three do not belong to any
// one module: they are promises about the whole curriculum. So they survive,
// behind a disclosure, as the thing you go back to rather than the thing you
// are shown again every visit.

import type { PlanDoc } from "@/lib/compose";
import { Assumptions } from "@/components/plan/Assumptions";

export function PlanCaveats({ doc }: { doc: PlanDoc }) {
  return (
    <>
      {doc.wontCover.length > 0 && (
        <section className="margined mt-14">
          <p className="rail">Excluded</p>
          <ul className="space-y-4">
            {doc.wontCover.map((o) => (
              <li key={o.topic} className="border-l-2 border-[color:var(--accent-line)] pl-4">
                <p className="text-sm font-medium text-[color:var(--ink)]">{o.topic}</p>
                <p className="mt-0.5 text-sm leading-6 text-[color:var(--muted)]">
                  {o.consequence}
                </p>
                <p className="text-sm leading-6 text-[color:var(--muted)]">
                  Learn it {o.whenToLearn.replace(/^(before|when|only)/i, (m) => m.toLowerCase())}
                </p>
              </li>
            ))}
          </ul>
        </section>
      )}

      {doc.cannotDo.length > 0 && (
        <section className="margined mt-14">
          <p className="rail" style={{ color: "var(--bad-ink)" }}>
            Cannot produce
          </p>
          <div className="note note-bad">
          <p className="text-sm leading-6">
            This content needs treatment we can&apos;t produce yet. We&apos;ll write
            it as prose — which is worse for this material, not equivalent.
          </p>
          <ul className="mt-4 space-y-3">
            {doc.cannotDo.map((c) => (
              <li key={c.what}>
                <p className="text-sm font-medium text-[color:var(--ink)]">{c.what}</p>
                <p className="text-sm leading-6 opacity-90">
                  Needed for: {c.concepts.join(" · ")}
                </p>
              </li>
            ))}
          </ul>
          </div>
        </section>
      )}

      <Assumptions assumptions={doc.assumptions} />
    </>
  );
}
