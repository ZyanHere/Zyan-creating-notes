const navigationItems = [
  "Projects",
  "Recent",
  "Templates",
  "Artifacts",
] as const;

const secondaryItems = ["Settings", "User profile"] as const;

export function Sidebar() {
  return (
    <aside className="flex w-full flex-col border-b border-[color:var(--line)] bg-[color:var(--sidebar)] px-5 py-6 lg:min-h-screen lg:w-72 lg:border-b-0 lg:border-r">
      <div className="flex items-center gap-3">
        <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-[color:var(--ink)] text-sm font-semibold text-white shadow-[0_14px_30px_rgba(22,34,51,0.16)]">
          NB
        </div>
        <div>
          <p className="text-sm font-medium uppercase tracking-[0.24em] text-[color:var(--muted)]">
            Workspace
          </p>
          <h1 className="text-lg font-semibold text-[color:var(--ink)]">
            Notes Bible
          </h1>
        </div>
      </div>

      <nav className="mt-10 flex gap-2 overflow-x-auto lg:block lg:space-y-2">
        {navigationItems.map((item, index) => (
          <a
            key={item}
            href="#"
            className={`inline-flex min-w-max items-center rounded-full px-4 py-2.5 text-sm font-medium transition-colors lg:flex lg:w-full lg:rounded-2xl ${
              index === 0
                ? "bg-white text-[color:var(--ink)] shadow-[0_10px_24px_rgba(28,39,53,0.08)]"
                : "text-[color:var(--muted)] hover:bg-white/70 hover:text-[color:var(--ink)]"
            }`}
          >
            {item}
          </a>
        ))}
      </nav>

      <div className="mt-8 rounded-[28px] border border-[color:var(--line)] bg-white/80 p-4 shadow-[0_16px_40px_rgba(33,44,61,0.06)]">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[color:var(--muted)]">
          Product Model
        </p>
        <div className="mt-4 space-y-2 text-sm text-[color:var(--ink)]">
          <p>Projects hold topic context.</p>
          <p>Workstreams separate purpose.</p>
          <p>Artifacts are concrete documents.</p>
        </div>
      </div>

      <div className="mt-auto hidden pt-8 lg:block">
        <div className="space-y-2">
          {secondaryItems.map((item) => (
            <a
              key={item}
              href="#"
              className="flex items-center rounded-2xl px-4 py-2.5 text-sm font-medium text-[color:var(--muted)] transition-colors hover:bg-white/70 hover:text-[color:var(--ink)]"
            >
              {item}
            </a>
          ))}
        </div>

        <div className="mt-6 rounded-[24px] bg-[color:var(--ink)] p-4 text-white">
          <p className="text-sm font-semibold">Aisha Rahman</p>
          <p className="mt-1 text-sm text-white/70">
            Product design and notes workspace
          </p>
        </div>
      </div>
    </aside>
  );
}
