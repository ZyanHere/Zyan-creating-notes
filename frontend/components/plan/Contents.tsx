// The contents page, in two framings.
//
// One module is a document, and this is its contents. Several modules are a
// curriculum, and each row is a PDF the learner will receive — a different
// promise, so it says so rather than looking like chapters of one book.
//
// Partition supplies the grouping, traversal the order, and scope the bullets
// beneath each part. The reader sees one list, because a contents page is how
// anyone judges whether they are being given the thing they wanted.

import type { ContentUnit } from "@/lib/compose";
import { depthWord } from "@/lib/compose";

export function Contents({
  units,
  orderNote,
  isCurriculum = false,
}: {
  units: ContentUnit[];
  orderNote: string | null;
  isCurriculum?: boolean;
}) {
  if (units.length === 0) return null;

  return (
    <section className="mt-10">
      <h2 className="eyebrow eyebrow-accent">
        {isCurriculum ? `${units.length} documents` : "Contents"}
      </h2>
      {isCurriculum && (
        <p className="mt-2 max-w-2xl text-sm leading-6 text-[color:var(--muted)]">
          Each of these is its own PDF, meant to be worked through on its own.
        </p>
      )}
      {orderNote && (
        <p className="mt-2 max-w-2xl text-sm leading-6 text-[color:var(--muted)]">{orderNote}</p>
      )}

      <ol className="mt-6 space-y-4">
        {units.map((unit, i) => (
          <li key={unit.heading} className="panel flex gap-4 p-5">
            <span
              aria-hidden
              className="mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-full border border-[color:var(--accent-line)] bg-[color:var(--accent-bg)] font-[family-name:var(--font-mono)] text-xs tabular-nums text-[color:var(--accent)]"
            >
              {i + 1}
            </span>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-baseline justify-between gap-x-4">
                <h3 className="text-base font-semibold tracking-[-0.01em] text-[color:var(--ink)]">
                  {unit.heading}
                </h3>
                {unit.extent && (
                  <span className="shrink-0 font-[family-name:var(--font-mono)] text-[0.6875rem] tabular-nums text-[color:var(--soft)]">
                    {unit.extent}
                  </span>
                )}
              </div>
              {/* The capability is what makes a module a module rather than a
                  chapter, so for a curriculum it leads — it is the thing the
                  reader is deciding about. */}
              {unit.capability && (
                <p className="mt-2 text-sm leading-6 text-[color:var(--ink)]">
                  <span className="eyebrow eyebrow-accent mr-1.5 align-[0.1em]">
                    Afterwards
                  </span>
                  {unit.capability}
                </p>
              )}
              <p className="mt-1 text-sm leading-6 text-[color:var(--muted)]">{unit.why}</p>

              {unit.items.length > 0 && (
                <ul className="mt-3.5 space-y-0.5 border-l border-[color:var(--line-strong)] pl-4">
                  {unit.items.map((item) => (
                    <li
                      key={item.concept}
                      className="group flex flex-wrap items-baseline justify-between gap-x-4 rounded-md py-0.5 transition-colors hover:bg-[color:var(--panel-strong)]"
                      title={item.why}
                    >
                      <span className="text-sm text-[color:var(--ink)]">{item.concept}</span>
                      <span className="shrink-0 font-[family-name:var(--font-mono)] text-[0.625rem] uppercase tracking-wider text-[color:var(--soft)] transition-colors group-hover:text-[color:var(--accent)]">
                        {depthWord(item.depth)}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}
