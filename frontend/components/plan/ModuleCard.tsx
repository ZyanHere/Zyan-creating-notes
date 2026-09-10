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

function Numeral({ module }: { module: ModuleState }) {
  const base =
    "grid h-7 w-7 shrink-0 place-items-center rounded-full font-[family-name:var(--font-mono)] text-xs tabular-nums";
  if (module.state === "done") {
    return (
      <span aria-hidden className={`${base} bg-[color:var(--ok)] text-[color:var(--canvas)]`}>
        ✓
      </span>
    );
  }
  if (module.state === "running") {
    return (
      <span
        aria-hidden
        className={`${base} bg-[color:var(--accent)] text-[color:var(--on-accent)]`}
      >
        {module.index}
      </span>
    );
  }
  return (
    <span
      aria-hidden
      className={`${base} border border-[color:var(--line-strong)] text-[color:var(--muted)]`}
    >
      {module.index}
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
      className={`overflow-hidden rounded-2xl border transition-colors ${
        m.state === "done"
          ? "border-[color:var(--ok-line)] bg-[color:var(--ok-bg)]"
          : m.state === "running"
            ? "border-[color:var(--accent-line)] bg-[color:var(--accent-bg)]"
            : "panel panel-lift"
      }`}
    >
      <div className="p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          {/* A real basis, not bare `flex-1`: with a zero basis the title
              shrinks to a one-word column while the shrink-0 action group keeps
              its width, which at 375px stacked the title under the buttons. */}
          <div className="flex min-w-0 flex-1 basis-64 items-start gap-3">
            <Numeral module={m} />
            <div className="min-w-0">
              <h3 className="text-base font-semibold leading-6 tracking-[-0.01em] text-[color:var(--ink)]">
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
                className="btn btn-primary px-4 py-2"
                title={busy ? "Another module is being written" : undefined}
              >
                Write it
              </button>
            )}
            {m.state === "running" && (
              <span className="inline-flex items-center gap-2 text-sm text-[color:var(--accent)]">
                <Spinner />
                Writing
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
              <button onClick={onWrite} disabled={busy} className="btn btn-primary px-4 py-2">
                Try again
              </button>
            )}
            {m.state === "done" && (
              <>
                <a
                  href={moduleArtifactUrl(projectId, m.index)}
                  target="_blank"
                  rel="noreferrer"
                  className="btn btn-primary px-4 py-2"
                >
                  Open
                </a>
                <a
                  href={moduleArtifactUrl(projectId, m.index, true)}
                  className="btn btn-ghost px-4 py-2"
                >
                  Download
                </a>
              </>
            )}
          </div>
        </div>

        {/* One row of facts, and one control that opens everything else about
            this module. `aria-expanded` rather than a styled details/summary,
            because the panel it controls is a sibling below the padding box. */}
        <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 font-[family-name:var(--font-mono)] text-[0.6875rem] uppercase tracking-wider text-[color:var(--soft)]">
          <span>
            {m.state === "done" && m.pages ? `${m.pages} pages` : m.extent ?? "—"}
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
            Written, but it doesn&apos;t match what was approved — open it to see
            what&apos;s missing.
          </p>
        )}
      </div>

      {expanded && (
        <div className="border-t border-[color:var(--line)] bg-[color:var(--panel-soft)]/60 px-5 py-4">
          {m.why_here && (
            <p className="text-sm leading-6 text-[color:var(--muted)]">{m.why_here}</p>
          )}

          {coverage.length > 0 ? (
            <ul className="mt-3 space-y-0.5 border-l border-[color:var(--line-strong)] pl-4">
              {coverage.map((c) => (
                <li
                  key={c.concept}
                  className="group flex flex-wrap items-baseline justify-between gap-x-4 rounded-md py-0.5 transition-colors hover:bg-[color:var(--panel-strong)]"
                  title={c.why}
                >
                  <span className="text-sm text-[color:var(--ink)]">{c.concept}</span>
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
            <div className="mt-4 rounded-xl border border-[color:var(--line)] bg-[color:var(--panel)] p-4">
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
