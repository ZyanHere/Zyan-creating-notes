export function NewProjectInput() {
  return (
    <section className="rounded-[32px] border border-[color:var(--line-strong)] bg-[color:var(--panel-strong)] p-5 shadow-[0_24px_60px_rgba(32,43,58,0.08)] sm:p-7">
      <div className="flex flex-col gap-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[color:var(--muted)]">
              New Project
            </p>
            <h2 className="mt-2 text-2xl font-semibold tracking-tight text-[color:var(--ink)]">
              What do you need notes on?
            </h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-[color:var(--muted)]">
              Start with a topic, course, or professional subject. The product
              will eventually turn this into a Project and recommend the right
              Workstream and note style.
            </p>
          </div>
          <span className="inline-flex rounded-full border border-[color:var(--line)] px-3 py-1 text-xs font-medium text-[color:var(--muted)]">
            UI placeholder
          </span>
        </div>

        <div className="rounded-[28px] border border-[color:var(--line)] bg-white p-3 shadow-[inset_0_1px_0_rgba(255,255,255,0.7)]">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <input
              type="text"
              aria-label="What do you need notes on?"
              placeholder="I need notes on Generative AI..."
              className="h-14 flex-1 rounded-[22px] border border-transparent bg-[color:var(--canvas)] px-5 text-base text-[color:var(--ink)] outline-none ring-0 placeholder:text-[color:var(--muted)] focus:border-[color:var(--line-strong)]"
            />
            <button
              type="button"
              className="inline-flex h-14 items-center justify-center rounded-[22px] bg-[color:var(--ink)] px-6 text-sm font-semibold text-white transition-transform hover:-translate-y-0.5"
            >
              Create -&gt;
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
