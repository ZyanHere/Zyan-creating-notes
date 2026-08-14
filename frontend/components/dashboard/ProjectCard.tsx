import type { Project } from "@/lib/mock-data";

type ProjectCardProps = {
  project: Project;
};

export function ProjectCard({ project }: ProjectCardProps) {
  return (
    <article className="group rounded-[28px] border border-[color:var(--line)] bg-white p-5 shadow-[0_20px_50px_rgba(27,40,56,0.06)] transition-all hover:-translate-y-1 hover:shadow-[0_28px_70px_rgba(27,40,56,0.1)]">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-4">
          <div
            className={`flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br ${project.accent} text-sm font-semibold text-white shadow-[0_10px_24px_rgba(22,34,51,0.18)]`}
          >
            {project.name
              .split(" ")
              .slice(0, 2)
              .map((part) => part[0])
              .join("")}
          </div>
          <div>
            <span className="inline-flex rounded-full bg-[color:var(--canvas)] px-3 py-1 text-xs font-medium text-[color:var(--muted)]">
              {project.topicTag}
            </span>
            <h3 className="mt-3 text-lg font-semibold tracking-tight text-[color:var(--ink)]">
              {project.name}
            </h3>
          </div>
        </div>
        <button
          type="button"
          className="rounded-full border border-[color:var(--line)] px-3 py-1 text-xs font-medium text-[color:var(--muted)] transition-colors hover:border-[color:var(--line-strong)] hover:text-[color:var(--ink)]"
        >
          Open
        </button>
      </div>

      <p className="mt-4 text-sm leading-6 text-[color:var(--muted)]">
        {project.description}
      </p>

      <dl className="mt-6 grid grid-cols-2 gap-3">
        <div className="rounded-[20px] bg-[color:var(--canvas)] px-4 py-3">
          <dt className="text-xs font-semibold uppercase tracking-[0.18em] text-[color:var(--muted)]">
            Workstreams
          </dt>
          <dd className="mt-2 text-lg font-semibold text-[color:var(--ink)]">
            {project.workstreamCount}
          </dd>
        </div>
        <div className="rounded-[20px] bg-[color:var(--canvas)] px-4 py-3">
          <dt className="text-xs font-semibold uppercase tracking-[0.18em] text-[color:var(--muted)]">
            Artifacts
          </dt>
          <dd className="mt-2 text-lg font-semibold text-[color:var(--ink)]">
            {project.artifactCount}
          </dd>
        </div>
      </dl>

      <div className="mt-6 flex items-center justify-between border-t border-[color:var(--line)] pt-4">
        <p className="text-sm text-[color:var(--muted)]">{project.updatedLabel}</p>
        <span className="text-sm font-medium text-[color:var(--ink)]">
          Topic workspace
        </span>
      </div>
    </article>
  );
}
