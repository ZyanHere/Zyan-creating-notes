"use client";

// One module: what it contains, and the button that writes it.
//
// THE MODULE'S SLICE OF THE PLAN LIVES ON THE MODULE. The generation screen
// used to list the modules and then, underneath, re-render the entire plan
// document — which is a second list of the same modules with the same concepts
// under them. Two lists of one thing, and the second one was built from the
// *current* decisions rather than from the approved snapshot, so after approval
// it was not even the promise that had been made.
//
// So each card carries its own approved contents. Collapsed by default, because
// a curriculum can be 25 modules and an always-open concept list is a wall
// rather than a page; one disclosure per module opens everything about that
// module — what it covers, and how the written document measured up.

import { moduleArtifactUrl, type ModuleState } from "@/lib/api";
import { depthWord } from "@/lib/compose";
import { FulfilmentReport } from "@/components/plan/Fulfilment";
import { Spinner } from "@/components/ui/Spinner";

/** "3 worked through · 5 explained" — the shape of a module at a glance.
 *
 *  Counts rather than a list: from the outside the useful question is how deep
 *  this one goes, not which twenty concepts are in it. */
function depthSummary(coverage: ModuleState["coverage"]): string {
  if (!coverage?.length) return "";
  const counts = new Map<string, number>();
  for (const c of coverage) {
    const word = depthWord(c.depth);
    counts.set(word, (counts.get(word) ?? 0) + 1);
  }
  return [...counts.entries()].map(([word, n]) => `${n} ${word}`).join(" · ");
}

/** A plate number in the margin. A figure, not a badge -- the row's left rule
 *  already carries the state, so the numeral only has to be readable. */
function Numeral({ module }: { module: ModuleState }) {
  const tone =
    module.state === "done"
      ? "text-[color:var(--ok)]"
      : module.state === "running"
        ? "text-[color:var(--accent)]"
        : "text-[color:var(--soft)]";
  return (
    <span
      aria-hidden
      className={`w-6 shrink-0 pt-1 font-[family-name:var(--font-mono)] text-[0.6875rem] tabular-nums ${tone}`}
    >
      {module.state === "done" ? "✓" : String(module.index).padStart(2, "0")}
    </span>
  );
}

export function ModuleCard({
  projectId,
  module: m,
  busy,
  expanded,
  onToggle,
  onWrite,
}: {
  projectId: string;
  module: ModuleState;
  busy: boolean;
  expanded: boolean;
  onToggle: () => void;
  onWrite: () => void;
}) {
  const coverage = m.coverage ?? [];
  const summary = depthSummary(coverage);

  return (
    <li
      className={`border-l-2 transition-colors ${
        m.state === "done"
          ? "border-[color:var(--ok)] bg-[color:var(--ok-bg)]"
          : m.state === "running"
            ? "border-[color:var(--accent)] bg-[color:var(--accent-bg)]"
            : "border-transparent hover:bg-[color:var(--panel-soft)]"
      }`}
    >
      <div className="py-5 pl-4 pr-1">
        <div className="flex flex-wrap items-start justify-between gap-3">
          {/* A real basis, not bare `flex-1`: with a zero basis the title
              shrinks to a one-word column while the shrink-0 action group keeps
              its width, which at 375px stacked the title under the buttons. */}
          <div className="flex min-w-0 flex-1 basis-64 items-start gap-3">
            <Numeral module={m} />
            <div className="min-w-0">
              <h3 className="font-[family-name:var(--font-serif)] text-[1.0625rem] leading-6 text-[color:var(--ink)]">
                {m.title}
              </h3>
              {m.capability && (
                <p className="mt-1 text-sm leading-6 text-[color:var(--muted)]">
                  <span className="eyebrow eyebrow-accent mr-1.5 align-[0.1em]">
                    Afterwards
                  </span>
                  {m.capability}
                </p>
              )}
            </div>
          </div>

          <div className="flex shrink-0 flex-wrap items-center gap-2">
            {m.state === "idle" && (
              <button
                onClick={onWrite}
                disabled={busy}
                className="btn btn-primary"
                title={busy ? "Another module is being written" : undefined}
              >
                Write it
              </button>
            )}
            {m.state === "running" && (
              <span className="inline-flex items-center gap-2 text-sm text-[color:var(--accent)]">
                <Spinner />
                writing · headless chromium
                {typeof m.seconds === "number" ? (
                  <span className="font-[family-name:var(--font-mono)] text-xs tabular-nums opacity-80">
                    {Math.round(m.seconds)}s
                  </span>
                ) : (
                  "…"
                )}
              </span>
            )}
            {m.state === "failed" && (
              <button onClick={onWrite} disabled={busy} className="btn btn-primary">
                Try again
              </button>
            )}
            {m.state === "done" && (
              <>
                <a
                  href={moduleArtifactUrl(projectId, m.index)}
                  target="_blank"
                  rel="noreferrer"
                  className="btn btn-primary"
                >
                  Open
                </a>
                <a
                  href={moduleArtifactUrl(projectId, m.index, true)}
                  className="btn btn-ghost"
                >
                  Download
                </a>
                {/* A document that does not match the approved plan is the one
                    case where the check has told the reader something is wrong
                    and offered nothing to do about it. Writing it again is the
                    fix, and it is often the whole fix -- the usual cause is a
                    call that failed rather than a model that cannot do it. */}
                {m.satisfied === false && (
                  <button
                    onClick={onWrite}
                    disabled={busy}
                    className="btn btn-ghost"
                    title={busy ? "Another module is being written" : undefined}
                  >
                    Write it again
                  </button>
                )}
              </>
            )}
          </div>
        </div>

        {/* One row of facts, and one control that opens everything else about
            this module. `aria-expanded` rather than a styled details/summary,
            because the panel it controls is a sibling below the padding box. */}
        <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 font-[family-name:var(--font-mono)] text-[0.6875rem] uppercase tracking-wider text-[color:var(--soft)]">
          <span>
            {m.state === "done" && m.pages
              ? `rendered · ${m.pages} pages`
              : m.extent ?? "—"}
          </span>
          <span aria-hidden className="opacity-40">
            ·
          </span>
          <span>{m.concepts.length} topics</span>
          {summary && (
            <>
              <span aria-hidden className="opacity-40">
                ·
              </span>
              <span className="normal-case tracking-normal">{summary}</span>
            </>
          )}
          <button
            onClick={onToggle}
            aria-expanded={expanded}
            className="ml-auto inline-flex items-center gap-1.5 uppercase tracking-wider text-[color:var(--muted)] transition-colors hover:text-[color:var(--accent)]"
          >
            {expanded ? "Hide" : "What's in it"}
            <span
              aria-hidden
              className={`text-[0.625rem] transition-transform ${expanded ? "rotate-90" : ""}`}
            >
              ▶
            </span>
          </button>
        </div>

        {m.state === "failed" && (
          <p className="mt-3 text-sm leading-6 text-[color:var(--bad-ink)]">
            This one didn&apos;t get written: {m.error}. Your approved plan is
            untouched, and the other modules are unaffected.
          </p>
        )}

        {m.state === "done" && m.satisfied === false && !expanded && (
          <p className="mt-3 text-sm leading-6 text-[color:var(--warn-ink)]">
            Written, but it doesn&apos;t match what was approved — open{" "}
            <button
              onClick={onToggle}
              className="underline decoration-[color:var(--warn-line)] underline-offset-4 hover:decoration-current"
            >
              what&apos;s in it
            </button>{" "}
            to see which part is missing and why.
          </p>
        )}
      </div>

      {expanded && (
        <div className="border-t border-[color:var(--line)] bg-[color:var(--panel-soft)]/60 py-4 pl-4 pr-1">
          {m.why_here && (
            <p className="text-sm leading-6 text-[color:var(--muted)]">{m.why_here}</p>
          )}

          {coverage.length > 0 ? (
            <ul className="mt-3 space-y-1">
              {coverage.map((c) => (
                <li
                  key={c.concept}
                  className="group flex flex-wrap items-baseline justify-between gap-x-4 border-b border-dotted border-[color:var(--line)] pb-1"
                  title={c.why}
                >
                  <span className="font-[family-name:var(--font-serif)] text-sm text-[color:var(--ink)]">
                    {c.concept}
                  </span>
                  <span className="shrink-0 font-[family-name:var(--font-mono)] text-[0.625rem] uppercase tracking-wider text-[color:var(--soft)] transition-colors group-hover:text-[color:var(--accent)]">
                    {depthWord(c.depth)}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            // A legacy snapshot, approved before depths were recorded per
            // module. The names are still worth showing.
            <p className="mt-3 text-sm leading-6 text-[color:var(--muted)]">
              {m.concepts.join(" · ")}
            </p>
          )}

          {m.fulfilment && <FulfilmentReport report={m.fulfilment} />}

          {m.representation?.stated_gaps?.length ? (
            <div className="mt-4 sheet-soft p-4">
              <p className="eyebrow">Figures we couldn&apos;t draw</p>
              <ul className="mt-2 space-y-1.5">
                {m.representation.stated_gaps.map((gap) => (
                  <li key={gap} className="text-sm leading-6 text-[color:var(--soft)]">
                    {gap}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      )}
    </li>
  );
}
