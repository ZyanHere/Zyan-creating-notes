// The plan, as the document it describes.
//
// Cover, contents, and what it won't cover — in that order, because that is the
// order someone reads a document they are deciding whether to want. The six
// decision records behind it are unchanged and one disclosure away.

import type { PlanDoc } from "@/lib/compose";
import { Contents } from "@/components/plan/Contents";
import { Assumptions } from "@/components/plan/Assumptions";

export function PlanDocument({ doc }: { doc: PlanDoc }) {
  return (
    <article>
      <header className="rounded-2xl border border-[color:var(--line)] bg-[color:var(--panel)] p-6 sm:p-8">
        <h1 className="text-3xl font-semibold tracking-tight text-[color:var(--ink)]">
          {doc.title}
        </h1>
        {doc.subtitle && (
          <p className="mt-2 max-w-2xl text-base leading-7 text-[color:var(--muted)]">
            {doc.subtitle}
          </p>
        )}

        {doc.meta.length > 0 && (
          <p className="mt-5 text-sm tabular-nums text-[color:var(--muted)]">
            {doc.meta.join("  ·  ")}
          </p>
        )}

        <dl className="mt-6 grid gap-x-6 gap-y-3 border-t border-[color:var(--line)] pt-5 sm:grid-cols-[9rem_1fr]">
          {doc.writtenFor && (
            <>
              <dt className="text-sm text-[color:var(--muted)]">Written for you</dt>
              <dd className="text-sm leading-6 text-[color:var(--ink)]">{doc.writtenFor}</dd>
            </>
          )}
          {doc.byTheEnd && (
            <>
              <dt className="text-sm text-[color:var(--muted)]">By the end</dt>
              <dd className="text-sm leading-6 text-[color:var(--ink)]">{doc.byTheEnd}</dd>
            </>
          )}
          {doc.capacity && (
            <>
              <dt className="text-sm text-[color:var(--muted)]">Fitting</dt>
              <dd className="text-sm leading-6 text-[color:var(--ink)]">{doc.capacity}</dd>
            </>
          )}
        </dl>

        {doc.stated.length > 0 && (
          <p className="mt-4 text-sm leading-6 text-[color:var(--muted)]">
            You told us: {doc.stated.join(" · ")}
          </p>
        )}
      </header>

      <Contents units={doc.contents} orderNote={doc.orderNote} />

      {doc.wontCover.length > 0 && (
        <section className="mt-10">
          <h2 className="text-xs font-semibold uppercase tracking-[0.24em] text-[color:var(--muted)]">
            What this won&apos;t cover
          </h2>
          <ul className="mt-4 space-y-4">
            {doc.wontCover.map((o) => (
              <li key={o.topic} className="border-l-2 border-[color:var(--line-strong)] pl-4">
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
        <section className="mt-10 rounded-2xl border border-red-200/80 bg-red-50/50 p-5">
          <h2 className="text-xs font-semibold uppercase tracking-[0.24em] text-red-900">
            What we can&apos;t give you for this subject
          </h2>
          <p className="mt-2 text-sm leading-6 text-red-900">
            This content needs treatment we can&apos;t produce yet. We&apos;ll write
            it as prose — which is worse for this material, not equivalent.
          </p>
          <ul className="mt-4 space-y-3">
            {doc.cannotDo.map((c) => (
              <li key={c.what}>
                <p className="text-sm font-medium text-[color:var(--ink)]">{c.what}</p>
                <p className="text-sm leading-6 text-red-900">
                  Needed for: {c.concepts.join(" · ")}
                </p>
              </li>
            ))}
          </ul>
        </section>
      )}

      <Assumptions assumptions={doc.assumptions} />
    </article>
  );
}
