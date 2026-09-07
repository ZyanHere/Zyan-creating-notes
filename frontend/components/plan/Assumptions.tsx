"use client";

// Visible by default, and compact.
//
// Semantics §3 makes anything the user did not mention the system's decision,
// and a decision the user cannot see is one they cannot correct. Behind a
// disclosure it is technically present and practically invisible, so the
// inferences themselves are always on screen; only the *reasoning* expands.

import { useState } from "react";
import type { Assumption } from "@/lib/compose";

export function Assumptions({ assumptions }: { assumptions: Assumption[] }) {
  const [open, setOpen] = useState(false);
  if (assumptions.length === 0) return null;

  const withDetail = assumptions.filter((a) => a.detail);

  return (
    <section className="mt-10 rounded-2xl border border-amber-200/70 bg-amber-50/50 p-5">
      <h2 className="text-xs font-semibold uppercase tracking-[0.24em] text-amber-900">
        We assumed — you didn&apos;t say, so we decided
      </h2>

      <ul className="mt-3 space-y-1.5">
        {assumptions.map((a) => (
          <li key={a.text} className="text-sm leading-6 text-[color:var(--ink)]">
            · {a.text}
            {open && a.detail && (
              <span className="block pl-3 text-sm leading-6 text-amber-900">{a.detail}</span>
            )}
          </li>
        ))}
      </ul>

      <div className="mt-3 flex flex-wrap items-center gap-3">
        <p className="text-sm text-amber-900">Say so below if any of these are wrong.</p>
        {withDetail.length > 0 && (
          <button
            onClick={() => setOpen((v) => !v)}
            className="text-sm text-amber-900 underline"
          >
            {open ? "Hide" : `Why these matter (${withDetail.length})`}
          </button>
        )}
      </div>
    </section>
  );
}
