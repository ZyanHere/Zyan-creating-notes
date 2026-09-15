// One previous commission, in the archive grid.
//
// A card here rather than a ruled row: the archive is a *pick one* surface,
// and a card bounds one thing you are choosing between. The ledger discipline
// survives inside it — docket in mono, title in the document's serif, status
// and figures in mono — so it is the same material as the rest of the app,
// just enclosed.
//
// Answers the two questions a list has to answer at a glance: which one is
// this, and how far did it get.

import Link from "next/link";
import type { ProjectSummary } from "@/lib/api";

type Tone = "accent" | "warn" | "muted";

function progress(p: ProjectSummary): { label: string; tone: Tone } {
  if (p.modules_total > 0 && p.modules_done > 0) {
    return {
      label:
        p.modules_done === p.modules_total
          ? `all ${p.modules_total} printed`
          : `${p.modules_done}/${p.modules_total} printed`,
      tone: "accent",
    };
  }
  if (p.approved) return { label: `${p.modules_total} to print`, tone: "accent" };
  switch (p.state) {
    case "planned":
      return { label: "awaiting sign-off", tone: "muted" };
    case "asking":
      return { label: "needs your answers", tone: "warn" };
    case "needs_subject":
      return { label: "needs a subject", tone: "warn" };
    case "ready":
      return { label: "ready to plan", tone: "muted" };
    default:
      // `unread`: stored, but the opening read never landed — usually a
      // provider outage. "ready to plan" here would be the archive claiming
      // work exists when none does.
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
  if (days < 7) return `${days}d ago`;
  return then.toLocaleDateString(undefined, { day: "numeric", month: "short" });
}

const TONE: Record<Tone, string> = {
  accent: "text-[color:var(--accent)]",
  warn: "text-[color:var(--warn-ink)]",
  muted: "text-[color:var(--soft)]",
};

export function ProjectCard({ project }: { project: ProjectSummary }) {
  const { label, tone } = progress(project);
  // Only worth showing when the plan has actually named the project something
  // other than what was typed; otherwise the card prints one sentence twice.
  const showQuery = project.query.trim() !== project.title.trim();
  const pct = project.modules_total
    ? (project.modules_done / project.modules_total) * 100
    : 0;

  return (
    <li className="card">
      <Link href={`/projects/${project.id}`} className="flex h-full flex-col p-4">
        <div className="flex items-baseline justify-between gap-3 font-[family-name:var(--font-mono)] text-[0.6875rem] text-[color:var(--soft)]">
          <span>#{project.id.slice(0, 6)}</span>
          <span>{when(project.created_at)}</span>
        </div>

        <h3 className="mt-2.5 font-[family-name:var(--font-serif)] text-[1.0625rem] italic leading-6 text-[color:var(--ink)]">
          {project.title}
        </h3>
        {showQuery && (
          <p className="mt-1.5 line-clamp-2 font-[family-name:var(--font-mono)] text-[0.6875rem] leading-5 text-[color:var(--muted)]">
            {project.query}
          </p>
        )}

        {/* The bar only exists where there is something to measure. An empty
            track under a project that was never approved implies a run that
            has not started, when in fact none was ever ordered. */}
        {project.modules_total > 0 && (
          <div className="track mt-4">
            <span style={{ width: `${pct}%` }} />
          </div>
        )}

        <p
          className={`mt-auto pt-3 font-[family-name:var(--font-mono)] text-[0.6875rem] ${TONE[tone]}`}
        >
          {label}
        </p>
      </Link>
    </li>
  );
}
