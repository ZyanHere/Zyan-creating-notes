// One project in the index.
//
// The index is how a Project stops being a session. Everything here exists to
// answer two questions from a list: *which one is this*, and *how far did it
// get* — because the list used to be four rows all reading
// "i need notes in agentic ai", which is a link back to work you cannot find.

import Link from "next/link";
import type { ProjectSummary } from "@/lib/api";

/** What the row says about where the project got to.
 *
 *  `tone` is the accent only when there is written work to come back to. A
 *  project that has never been read is not a warning — it is just empty — so it
 *  stays quiet rather than competing with the ones that have something in them. */
function progress(p: ProjectSummary): { label: string; tone: "accent" | "muted" | "warn" } {
  if (p.modules_total > 0 && p.modules_done > 0) {
    return {
      label:
        p.modules_done === p.modules_total
          ? `all ${p.modules_total} written`
          : `${p.modules_done} of ${p.modules_total} written`,
      tone: "accent",
    };
  }
  if (p.approved) {
    return { label: `${p.modules_total} to write`, tone: "warn" };
  }
  switch (p.state) {
    case "planned":
      return { label: "plan not approved", tone: "warn" };
    case "asking":
      return { label: "needs your answers", tone: "warn" };
    case "needs_subject":
      return { label: "needs a subject", tone: "warn" };
    case "ready":
      return { label: "ready to plan", tone: "muted" };
    default:
      // `unread`: stored, but the opening read never landed — usually a
      // provider outage. Saying "ready to plan" here would be the index
      // claiming work exists when none does.
      return { label: "never read", tone: "muted" };
  }
}

/** Dates in a list are for telling rows apart, not for logging. */
function when(iso: string): string {
  const then = new Date(iso);
  if (Number.isNaN(then.getTime())) return "";
  const days = Math.floor((Date.now() - then.getTime()) / 86_400_000);
  if (days <= 0) return "today";
  if (days === 1) return "yesterday";
  if (days < 7) return `${days} days ago`;
  return then.toLocaleDateString(undefined, { day: "numeric", month: "short" });
}

export function ProjectRow({ project }: { project: ProjectSummary }) {
  const { label, tone } = progress(project);
  // Only worth showing when the plan has actually renamed the project;
  // otherwise the row would print the same sentence twice.
  const showQuery = project.query.trim() !== project.title.trim();

  return (
    <li>
      <Link
        href={`/projects/${project.id}`}
        className="group flex items-start gap-3 rounded-xl border border-[color:var(--line)] bg-[color:var(--panel-soft)] px-4 py-3 transition-colors hover:border-[color:var(--accent-line)] hover:bg-[color:var(--panel)]"
      >
        <span
          aria-hidden
          className={`mt-2 h-1.5 w-1.5 shrink-0 rounded-full transition-colors ${
            tone === "accent"
              ? "bg-[color:var(--accent)]"
              : "bg-[color:var(--soft)] group-hover:bg-[color:var(--accent)]"
          }`}
        />

        <span className="min-w-0 flex-1">
          <span className="block truncate text-sm font-medium text-[color:var(--ink)]">
            {project.title}
          </span>
          {showQuery && (
            <span className="mt-0.5 block truncate text-sm text-[color:var(--muted)]">
              {project.query}
            </span>
          )}
          <span className="mt-1 flex flex-wrap items-center gap-x-2 font-[family-name:var(--font-mono)] text-[0.6875rem] uppercase tracking-wider">
            <span
              className={
                tone === "accent"
                  ? "text-[color:var(--accent)]"
                  : tone === "warn"
                    ? "text-[color:var(--warn-ink)]"
                    : "text-[color:var(--soft)]"
              }
            >
              {label}
            </span>
            <span aria-hidden className="text-[color:var(--soft)] opacity-50">
              ·
            </span>
            <span className="text-[color:var(--soft)]">{when(project.created_at)}</span>
          </span>
        </span>

        <span
          aria-hidden
          className="mt-1 shrink-0 text-[color:var(--soft)] transition-all group-hover:translate-x-0.5 group-hover:text-[color:var(--accent)]"
        >
          →
        </span>
      </Link>
    </li>
  );
}
