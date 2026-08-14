import type { RecentActivityItem } from "@/lib/mock-data";

type RecentActivityProps = {
  items: RecentActivityItem[];
};

const activityTone: Record<RecentActivityItem["type"], string> = {
  generated: "bg-cyan-100 text-cyan-700",
  updated: "bg-amber-100 text-amber-700",
  created: "bg-emerald-100 text-emerald-700",
};

export function RecentActivity({ items }: RecentActivityProps) {
  return (
    <section className="rounded-[28px] border border-[color:var(--line)] bg-white p-5 shadow-[0_16px_36px_rgba(27,40,56,0.05)]">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[color:var(--muted)]">
            Recent
          </p>
          <h2 className="mt-2 text-xl font-semibold tracking-tight text-[color:var(--ink)]">
            Recent activity
          </h2>
        </div>
        <button
          type="button"
          className="rounded-full border border-[color:var(--line)] px-3 py-1 text-xs font-medium text-[color:var(--muted)]"
        >
          Static feed
        </button>
      </div>

      <div className="mt-5 space-y-3">
        {items.map((item) => (
          <div
            key={`${item.title}-${item.project}`}
            className="flex items-start justify-between gap-4 rounded-[22px] bg-[color:var(--canvas)] px-4 py-4"
          >
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <span
                  className={`rounded-full px-2.5 py-1 text-xs font-semibold ${activityTone[item.type]}`}
                >
                  {item.type}
                </span>
                <p className="text-sm font-semibold text-[color:var(--ink)]">
                  {item.title}
                </p>
              </div>
              <p className="mt-2 text-sm text-[color:var(--muted)]">
                {item.project}
              </p>
            </div>
            <p className="text-sm text-[color:var(--muted)]">{item.when}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
