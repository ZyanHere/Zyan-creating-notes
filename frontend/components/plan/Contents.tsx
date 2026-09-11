// The contents page, in two framings.
//
// One module is a document, and this is its contents. Several modules are a
// curriculum, and each row is a PDF the learner will receive — a different
// promise, so it says so rather than looking like chapters of one book.
//
// Partition supplies the grouping, traversal the order, and scope the bullets
// beneath each part. The reader sees one list, because a contents page is how
// anyone judges whether they are being given the thing they wanted.
//
// Set as a contents page, not as cards: the figure in the margin, the title in
// the measure, the treatment in a right-hand column you can scan straight down.

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
    <section className="margined mt-14">
      <p className="rail">{isCurriculum ? `${units.length} documents` : "Contents"}</p>
      <div>
        {isCurriculum && (
          <p className="max-w-[58ch] text-sm leading-6 text-[color:var(--muted)]">
            Each of these is its own PDF, meant to be worked through on its own.
          </p>
        )}
        {orderNote && (
          <p className="mt-2 max-w-[58ch] text-sm leading-6 text-[color:var(--muted)]">
            {orderNote}
          </p>
        )}

        <ol className="ledger mt-6 border-t border-[color:var(--line)]">
          {units.map((unit, i) => (
            <li key={unit.heading} className="py-5">
              <div className="flex items-baseline gap-4">
                <span
                  aria-hidden
                  className="w-6 shrink-0 font-[family-name:var(--font-mono)] text-[0.6875rem] tabular-nums text-[color:var(--accent)]"
                >
                  {String(i + 1).padStart(2, "0")}
                </span>
                <h3 className="min-w-0 flex-1 font-[family-name:var(--font-serif)] text-[1.0625rem] leading-6 text-[color:var(--ink)]">
                  {unit.heading}
                </h3>
                {unit.extent && (
                  <span className="shrink-0 font-[family-name:var(--font-mono)] text-[0.6875rem] tabular-nums text-[color:var(--soft)]">
                    {unit.extent}
                  </span>
                )}
              </div>

              <div className="mt-2 pl-10">
                {/* The capability is what makes a module a module rather than a
                    chapter, so for a curriculum it leads — it is the thing the
                    reader is deciding about. */}
                {unit.capability && (
                  <p className="max-w-[58ch] text-sm leading-6 text-[color:var(--ink)]">
                    <span className="eyebrow eyebrow-accent mr-1.5 align-[0.1em]">
                      Afterwards
                    </span>
                    {unit.capability}
                  </p>
                )}
                <p className="mt-1 max-w-[58ch] text-sm leading-6 text-[color:var(--muted)]">
                  {unit.why}
                </p>

                {unit.items.length > 0 && (
                  <ul className="mt-3.5 space-y-1">
                    {unit.items.map((item) => (
                      <li
                        key={item.concept}
                        className="flex flex-wrap items-baseline justify-between gap-x-4 border-b border-dotted border-[color:var(--line)] pb-1"
                        title={item.why}
                      >
                        <span className="font-[family-name:var(--font-serif)] text-sm text-[color:var(--ink)]">
                          {item.concept}
                        </span>
                        <span className="shrink-0 font-[family-name:var(--font-mono)] text-[0.625rem] uppercase tracking-wider text-[color:var(--soft)]">
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
      </div>
    </section>
  );
}
