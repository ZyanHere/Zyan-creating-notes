// The plan, whole, on one page.
//
// Section order is fixed by Plan-Gate-Milestone §6. The one rule that is not a
// layout preference: WE DECIDED renders at the same visual weight as YOU SAID
// and is never collapsed. Semantics §3 makes silence the system's decision, and
// a decision the user cannot see is one they cannot correct — if this reads as
// a muted footnote, the lock is cosmetic.

import type { Decisions, Question } from "@/lib/api";

function Label({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="text-xs font-semibold uppercase tracking-[0.24em] text-[color:var(--muted)]">
      {children}
    </h2>
  );
}

function Section({
  title,
  changed,
  children,
}: {
  title: string;
  changed?: boolean;
  children: React.ReactNode;
}) {
  return (
    <section className="border-t border-[color:var(--line)] py-7 first:border-t-0">
      <div className="flex items-baseline gap-3">
        <Label>{title}</Label>
        {changed && (
          <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-amber-900">
            changed
          </span>
        )}
      </div>
      <div className="mt-4">{children}</div>
    </section>
  );
}

export function PlanBody({
  decisions,
  extent,
  questions,
  changed = [],
}: {
  decisions: Decisions;
  extent: string;
  questions: Question[];
  changed?: string[];
}) {
  const s = decisions.interpret_situation;
  const units = decisions.partition?.units ?? [];
  const order = decisions.traversal?.sequence ?? units.map((u) => u.heading);
  const byHeading = new Map(units.map((u) => [u.heading, u]));
  const has = (k: string) => changed.includes(k);

  return (
    <div>
      {s && (
        <Section title="Read as" changed={has("interpret_situation")}>
          <dl className="grid gap-x-6 gap-y-2 sm:grid-cols-[8rem_1fr]">
            {[
              ["Job", s.job],
              ["For", s.purpose],
              ["Assumes", s.entry_point],
              ["Afterwards", s.target_capability],
              ...(s.capacity ? [["Capacity", s.capacity]] : []),
            ].map(([k, v]) => (
              <div key={k as string} className="contents">
                <dt className="text-sm text-[color:var(--muted)]">{k}</dt>
                <dd className="text-sm leading-6 text-[color:var(--ink)]">{v}</dd>
              </div>
            ))}
          </dl>
        </Section>
      )}

      {s && (s.stated.length > 0 || s.inferred.length > 0) && (
        <Section title="What this rests on" changed={has("interpret_situation")}>
          <div className="grid gap-6 sm:grid-cols-2">
            <div>
              <p className="text-sm font-medium text-[color:var(--ink)]">You said</p>
              <ul className="mt-2 space-y-1.5">
                {s.stated.length === 0 && (
                  <li className="text-sm text-[color:var(--muted)]">
                    Nothing specific.
                  </li>
                )}
                {s.stated.map((c) => (
                  <li key={c} className="text-sm leading-6 text-[color:var(--ink)]">
                    · {c}
                  </li>
                ))}
              </ul>
            </div>
            {/* Same weight as the column beside it. Not a footnote. */}
            <div className="rounded-xl border border-amber-200/70 bg-amber-50/60 p-4">
              <p className="text-sm font-medium text-[color:var(--ink)]">
                We decided (you didn&apos;t say)
              </p>
              <ul className="mt-2 space-y-1.5">
                {s.inferred.map((c) => (
                  <li key={c} className="text-sm leading-6 text-[color:var(--ink)]">
                    · {c}
                  </li>
                ))}
              </ul>
              <p className="mt-3 text-xs leading-5 text-[color:var(--muted)]">
                Anything you didn&apos;t mention is ours to decide. Say so if any of
                it is wrong.
              </p>
            </div>
          </div>
        </Section>
      )}

      {questions.length > 0 && (
        <Section title={`Open (${questions.length})`} changed={has("intake_strategy")}>
          <ul className="space-y-4">
            {questions.map((q) => (
              <li
                key={q.question}
                className="rounded-xl border border-[color:var(--line)] bg-[color:var(--panel-soft)] p-4"
              >
                <p className="text-sm font-medium text-[color:var(--ink)]">
                  {q.question}
                </p>
                <p className="mt-1.5 text-sm leading-6 text-[color:var(--muted)]">
                  Matters because: {q.why_it_matters}
                </p>
                <ul className="mt-2 space-y-1">
                  {q.options.map((o) => (
                    <li
                      key={o.label}
                      className="text-sm leading-6 text-[color:var(--muted)]"
                    >
                      · <span className="text-[color:var(--ink)]">{o.label}</span> —{" "}
                      {o.implication}
                    </li>
                  ))}
                </ul>
                <p className="mt-1 text-sm leading-6 text-[color:var(--muted)]">
                  Assumed: {q.default_label}
                </p>
              </li>
            ))}
          </ul>
        </Section>
      )}

      {decisions.scope && (
        <Section
          title={`Covers (${decisions.scope.covered.length})`}
          changed={has("scope")}
        >
          <ul className="space-y-3">
            {decisions.scope.covered.map((c) => (
              <li key={c.concept}>
                <p className="text-sm font-medium text-[color:var(--ink)]">
                  {c.concept}{" "}
                  <span className="font-normal text-[color:var(--muted)]">
                    — {c.depth}
                  </span>
                </p>
                <p className="text-sm leading-6 text-[color:var(--muted)]">{c.why}</p>
              </li>
            ))}
          </ul>
          {decisions.scope.cut.length > 0 && (
            <p className="mt-4 text-sm text-[color:var(--muted)]">
              Cut for capacity: {decisions.scope.cut.join(", ")}
            </p>
          )}
        </Section>
      )}

      {decisions.consequence && decisions.consequence.exclusions.length > 0 && (
        <Section
          title={`Deliberately not (${decisions.consequence.exclusions.length})`}
          changed={has("consequence")}
        >
          <ul className="space-y-4">
            {decisions.consequence.exclusions.map((e) => (
              <li key={e.topic}>
                <p className="text-sm font-medium text-[color:var(--ink)]">{e.topic}</p>
                <p className="text-sm leading-6 text-[color:var(--muted)]">
                  Without it: {e.consequence}
                </p>
                <p className="text-sm leading-6 text-[color:var(--muted)]">
                  Learn it: {e.when_to_learn}
                </p>
              </li>
            ))}
          </ul>
        </Section>
      )}

      {units.length > 0 && (
        <Section
          title={`Units (${units.length})`}
          changed={has("partition") || has("traversal")}
        >
          <ol className="space-y-3">
            {order.map((heading, i) => (
              <li key={heading} className="flex gap-3">
                <span className="text-sm tabular-nums text-[color:var(--muted)]">
                  {i + 1}.
                </span>
                <div>
                  <p className="text-sm font-medium text-[color:var(--ink)]">
                    {heading}
                  </p>
                  <p className="text-sm leading-6 text-[color:var(--muted)]">
                    {byHeading.get(heading)?.why_here}
                  </p>
                </div>
              </li>
            ))}
          </ol>
          {decisions.traversal?.why && (
            <p className="mt-4 text-sm leading-6 text-[color:var(--muted)]">
              Order: {decisions.traversal.why}
            </p>
          )}
        </Section>
      )}

      <Section title="Extent" changed={has("scope")}>
        <p className="text-sm leading-6 text-[color:var(--ink)]">{extent}</p>
        <p className="mt-1 text-xs text-[color:var(--muted)]">
          Derived from the depths above, not written separately.
        </p>
      </Section>
    </div>
  );
}
