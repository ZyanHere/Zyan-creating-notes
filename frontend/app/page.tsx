import { NewProjectInput } from "@/components/dashboard/NewProjectInput";
import { ProjectCard } from "@/components/dashboard/ProjectCard";
import { RecentActivity } from "@/components/dashboard/RecentActivity";
import { SectionHeading } from "@/components/dashboard/SectionHeading";
import { Sidebar } from "@/components/dashboard/Sidebar";
import { TemplateCard } from "@/components/dashboard/TemplateCard";
import { projects, recentActivity, templates } from "@/lib/mock-data";

export default function Home() {
  return (
    <div className="min-h-screen bg-[color:var(--canvas)]">
      <div className="mx-auto flex min-h-screen w-full max-w-[1600px] flex-col lg:flex-row">
        <Sidebar />

        <main className="flex-1 px-4 py-4 sm:px-6 sm:py-6 lg:px-8 lg:py-8">
          <div className="rounded-[36px] border border-white/60 bg-[color:var(--panel)] p-5 shadow-[0_30px_80px_rgba(31,42,58,0.08)] sm:p-8">
            <header className="flex flex-col gap-5 border-b border-[color:var(--line)] pb-8 md:flex-row md:items-end md:justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.28em] text-[color:var(--muted)]">
                  Projects
                </p>
                <h1 className="mt-3 text-4xl font-semibold tracking-tight text-[color:var(--ink)]">
                  Your Projects
                </h1>
                <p className="mt-3 max-w-2xl text-sm leading-6 text-[color:var(--muted)] sm:text-base">
                  Create, organize, and generate notes around the topics you
                  care about.
                </p>
              </div>

              <button
                type="button"
                className="inline-flex h-12 items-center justify-center rounded-full border border-[color:var(--line-strong)] bg-white px-5 text-sm font-semibold text-[color:var(--ink)] shadow-[0_12px_30px_rgba(31,42,58,0.06)]"
              >
                + New Project
              </button>
            </header>

            <div className="mt-8">
              <NewProjectInput />
            </div>

            <section className="mt-10">
              <SectionHeading
                eyebrow="Workspace"
                title="Topic-based projects"
                description="Each Project is a persistent topic workspace. Workstreams, plans, and artifacts live inside it, so the dashboard reinforces the product model instead of a course or progress tracker."
              />

              <div className="mt-6 grid gap-5 xl:grid-cols-2">
                {projects.map((project) => (
                  <ProjectCard key={project.name} project={project} />
                ))}
              </div>
            </section>

            <div className="mt-10 grid gap-6 xl:grid-cols-[1.3fr_0.9fr]">
              <section className="rounded-[28px] border border-[color:var(--line)] bg-[color:var(--panel-soft)] p-5 shadow-[0_16px_36px_rgba(27,40,56,0.04)]">
                <SectionHeading
                  eyebrow="Templates"
                  title="Explore Templates"
                  description="How do you want your notes presented? These are visual previews only for now, with no selection logic attached yet."
                />
                <div className="mt-5 grid gap-4 md:grid-cols-2">
                  {templates.map((template) => (
                    <TemplateCard key={template.name} template={template} />
                  ))}
                </div>
              </section>

              <RecentActivity items={recentActivity} />
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
