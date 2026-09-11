// The project masthead and its stage rail.
//
// A project is the durable object; this is the paperwork attached to it. The
// docket number is the first six of the project id — short enough to read
// aloud, long enough to tell two "agentic ai" projects apart, and already the
// thing in the URL.
//
// The stage rail says where the job has got to: read → plan → sign → print.
// It is a STATUS INDICATOR, NOT NAVIGATION. Every value is derived from data
// already on the page (`view.state` and whether a commitment exists), and
// nothing here is clickable — a stage you cannot skip to should not look like
// a link.

import Link from "next/link";

const STAGES = ["read", "plan", "sign", "print"] as const;

/** Which stage the job is standing in. `unread` is before everything: the
 *  opening read never landed, so not even the first stage is done. */
function stageIndex(state: string, approved: boolean): number {
  if (approved) return 3;
  if (state === "planned") return 2;
  if (state === "ready") return 1;
  return 0;
}

export function Docket({
  id,
  title,
  state,
  approved,
}: {
  id: string;
  title: string;
  state: string;
  approved: boolean;
}) {
  const here = stageIndex(state, approved);

  return (
    <header className="border-b border-[color:var(--line-strong)] pb-3">
      <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
        <Link
          href="/"
          className="shrink-0 font-[family-name:var(--font-mono)] text-sm font-semibold tracking-[0.2em] text-[color:var(--ink)] transition-colors hover:text-[color:var(--accent)]"
        >
          MY<span className="text-[color:var(--accent)]">NOTES</span>
        </Link>
        <span className="shrink-0 font-[family-name:var(--font-mono)] text-[0.6875rem] text-[color:var(--soft)]">
          #{id.slice(0, 6)}
        </span>
        <span className="min-w-0 flex-1 truncate font-[family-name:var(--font-serif)] text-[0.9375rem] text-[color:var(--muted)]">
          {title}
        </span>
      </div>

      <ol
        className="mt-2.5 flex flex-wrap items-center gap-x-2 font-[family-name:var(--font-mono)] text-[0.6875rem] uppercase tracking-[0.14em]"
        aria-label={`Stage: ${STAGES[here]}`}
      >
        {STAGES.map((stage, i) => (
          <li key={stage} className="flex items-center gap-2">
            {i > 0 && (
              <span aria-hidden className="text-[color:var(--soft)] opacity-40">
                ·
              </span>
            )}
            <span
              aria-current={i === here ? "step" : undefined}
              className={
                i === here
                  ? "text-[color:var(--accent)]"
                  : i < here
                    ? "text-[color:var(--muted)]"
                    : "text-[color:var(--soft)] opacity-50"
              }
            >
              {stage}
            </span>
          </li>
        ))}
      </ol>
    </header>
  );
}
