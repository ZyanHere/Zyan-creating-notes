// The contents page. Partition supplies the grouping, traversal the order, and
// scope the bullets under each part — but the reader sees one list, because a
// contents page is how anyone judges whether a document is the one they want.

import type { ContentUnit } from "@/lib/compose";
import { depthWord } from "@/lib/compose";

export function Contents({ units, orderNote }: { units: ContentUnit[]; orderNote: string | null }) {
  if (units.length === 0) return null;

  return (
    <section className="mt-10">
      <h2 className="text-xs font-semibold uppercase tracking-[0.24em] text-[color:var(--muted)]">
        Contents
      </h2>
      {orderNote && (
        <p className="mt-2 max-w-2xl text-sm leading-6 text-[color:var(--muted)]">{orderNote}</p>
      )}

      <ol className="mt-6 space-y-7">
        {units.map((unit, i) => (
          <li key={unit.heading} className="flex gap-4">
            <span className="mt-0.5 w-6 shrink-0 text-right text-sm tabular-nums text-[color:var(--muted)]">
              {i + 1}
            </span>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-baseline justify-between gap-x-4">
                <h3 className="text-base font-medium text-[color:var(--ink)]">{unit.heading}</h3>
                {unit.extent && (
                  <span className="text-sm tabular-nums text-[color:var(--muted)]">
                    {unit.extent}
                  </span>
                )}
              </div>
              <p className="mt-1 text-sm leading-6 text-[color:var(--muted)]">{unit.why}</p>

              {unit.items.length > 0 && (
                <ul className="mt-3 space-y-1.5 border-l border-[color:var(--line)] pl-4">
                  {unit.items.map((item) => (
                    <li
                      key={item.concept}
                      className="flex flex-wrap items-baseline justify-between gap-x-4"
                      title={item.why}
                    >
                      <span className="text-sm text-[color:var(--ink)]">{item.concept}</span>
                      <span className="text-xs text-[color:var(--muted)]">
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
