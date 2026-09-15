// The plan, as the document it describes — a proof.
//
// Cover, contents, and what it won't cover, in that order, because that is the
// order someone reads a document they are deciding whether to want. The six
// decision records behind it are unchanged and one disclosure away.
//
// This is the ONE place the print metaphor becomes literal: registration marks
// on the corners, and the title set in the same serif the PDF uses. A proof is
// the thing a press shows you before it runs, and that is exactly what this
// screen is for. Used once — corner ticks on every card would be a texture, not
// an idea.

import type { PlanDoc } from "@/lib/compose";
import { Contents } from "@/components/plan/Contents";
import { PlanCaveats } from "@/components/plan/PlanCaveats";

export function PlanDocument({ doc }: { doc: PlanDoc }) {
  return (
    <article>
      <header className="sheet marks relative p-6 sm:p-10">
        <h1 className="max-w-[26ch] font-[family-name:var(--font-serif)] text-[1.75rem] font-normal leading-[1.15] tracking-[-0.01em] text-[color:var(--ink)] sm:text-[2.25rem]">
          {doc.title}
        </h1>
        {doc.subtitle && (
          <p className="mt-3 max-w-[58ch] font-[family-name:var(--font-serif)] text-base leading-7 text-[color:var(--muted)]">
            {doc.subtitle}
          </p>
        )}

        {doc.meta.length > 0 && (
          <p className="mt-6 flex flex-wrap items-center gap-x-2.5 gap-y-1 font-[family-name:var(--font-mono)] text-[0.6875rem] uppercase tracking-wider tabular-nums text-[color:var(--soft)]">
            {doc.meta.map((m, i) => (
              <span key={m} className="flex items-center gap-2.5">
                {i > 0 && (
                  <span aria-hidden className="text-[color:var(--accent)] opacity-60">
                    /
                  </span>
                )}
                {m}
              </span>
            ))}
          </p>
        )}

        <dl className="mt-7 grid gap-x-6 gap-y-3 border-t border-[color:var(--line)] pt-6 sm:grid-cols-[9rem_1fr]">
          {doc.writtenFor && (
            <>
              <dt className="eyebrow text-[0.625rem] sm:pt-1">Written for</dt>
              <dd className="text-sm leading-6 text-[color:var(--ink)]">{doc.writtenFor}</dd>
            </>
          )}
          {doc.byTheEnd && (
            <>
              <dt className="eyebrow text-[0.625rem] sm:pt-1">By the end</dt>
              <dd className="text-sm leading-6 text-[color:var(--ink)]">{doc.byTheEnd}</dd>
            </>
          )}
          {doc.capacity && (
            <>
              <dt className="eyebrow text-[0.625rem] sm:pt-1">Fitting</dt>
              <dd className="text-sm leading-6 text-[color:var(--ink)]">{doc.capacity}</dd>
            </>
          )}
        </dl>

        {doc.stated.length > 0 && (
          <p className="mt-6 border-t border-[color:var(--line)] pt-4 text-sm leading-6 text-[color:var(--soft)]">
            <span className="eyebrow mr-1.5 align-[0.1em]">You said</span>
            {doc.stated.join(" · ")}
          </p>
        )}
      </header>

      <Contents
        units={doc.contents}
        orderNote={doc.orderNote}
        isCurriculum={doc.isCurriculum}
      />

      <PlanCaveats doc={doc} />
    </article>
  );
}
