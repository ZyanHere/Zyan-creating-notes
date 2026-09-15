"use client";

// The approved curriculum, as a list of documents you can write one at a time.
//
// Not a batch button. The curriculum names N modules and each is its own PDF;
// you write the next one when you want it, in whatever order suits you. The
// approved plan is never rewritten by any of this — writing module 4 cannot
// change what module 5 was approved to contain.
//
// Polled rather than awaited: a module is several model calls plus a browser
// render, minutes on the free tier.

import { useCallback, useEffect, useRef, useState } from "react";
import { api, projectExportUrl, type ModuleState } from "@/lib/api";
import { ModuleCard } from "@/components/plan/ModuleCard";

const POLL_MS = 2500;

export function Modules({ projectId }: { projectId: string }) {
  const [modules, setModules] = useState<ModuleState[] | null>(null);
  const [open, setOpen] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const poll = useCallback(async () => {
    try {
      const { modules: next } = await api.listModules(projectId);
      setModules(next);
      if (next.some((m) => m.state === "running")) {
        timer.current = setTimeout(poll, POLL_MS);
      }
    } catch (e) {
      // A failed poll is not a failed generation — the work continues on the
      // server. Say so rather than implying the module was lost.
      setError(
        `Lost contact while waiting: ${e instanceof Error ? e.message : String(e)}. ` +
          `Writing may still be going — reload to check.`,
      );
    }
  }, [projectId]);

  useEffect(() => {
    poll();
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, [poll]);

  const write = useCallback(
    async (index: number) => {
      setError(null);
      setModules((ms) =>
        ms?.map((m) => (m.index === index ? { ...m, state: "running" } : m)) ?? ms,
      );
      try {
        await api.generateModule(projectId, index);
        poll();
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
        poll();
      }
    },
    [projectId, poll],
  );

  if (!modules) return null;

  const done = modules.filter((m) => m.state === "done").length;
  const busy = modules.some((m) => m.state === "running");
  const next = modules.find((m) => m.state === "idle");
  const allPrinted = done === modules.length;

  return (
    <section className="margined mt-14">
      <p className="rail">{modules.length === 1 ? "Document" : "Documents"}</p>
      <div>
      <div className="flex flex-wrap items-baseline justify-between gap-x-4">
        <h2 className="font-[family-name:var(--font-serif)] text-[1.25rem] text-[color:var(--ink)]">
          {allPrinted ? "Printed" : busy ? "On the press" : "Ready to print"}
        </h2>
        <div className="flex items-center gap-3">
          <p className="font-[family-name:var(--font-mono)] text-xs tracking-wide text-[color:var(--muted)]">
            <span className="text-[color:var(--accent)]">{done}</span>/{modules.length}
            {" "}printed
          </p>
          {/* A curriculum is several PDFs; fetching 25 of them one at a time is
              not a download, it is a chore. Hidden rather than disabled at zero
              — there is nothing to explain about a button for files that do not
              exist yet. A plain link, because the browser should handle the
              save; `download` lets the server's filename stand. */}
          {done > 0 && (
            <a href={projectExportUrl(projectId)} download className="btn btn-ghost">
              Download all ({done})
            </a>
          )}
        </div>
      </div>

      {/* A bar, because "2 of 3" is a fact and this is a feeling. Each module
          takes minutes, so the run is long enough to want a shape. */}
      <div
        className="mt-3 h-1 w-full overflow-hidden rounded-full bg-[color:var(--panel-strong)]"
        role="progressbar"
        aria-valuenow={done}
        aria-valuemin={0}
        aria-valuemax={modules.length}
      >
        <div
          className="h-full rounded-full bg-[color:var(--accent)] transition-[width] duration-500"
          style={{ width: `${(done / modules.length) * 100}%` }}
        />
      </div>
      <p className="mt-1 text-sm leading-6 text-[color:var(--muted)]">
        {modules.length === 1
          ? "Write it when you're ready."
          : "Each is its own PDF. Write them one at a time, in any order."}
      </p>

      {/* Two asides, never both. Each is about what the press is doing right
          now, so neither appears on a screen it would not be true of. */}
      {busy && (
        <p className="aside mt-3 max-w-[54ch]">
          yes. it&apos;s slow. one inference call per section, run one at a time,
          on a free tier. batching them is the obvious fix and it isn&apos;t built.
        </p>
      )}
      {!busy && allPrinted && (
        <p className="aside mt-3 max-w-[54ch]">
          planned, written, rendered and checked against what you approved. the
          whole pipeline held.
        </p>
      )}

      <ol className="ledger mt-5 border-t border-[color:var(--line)]">
        {modules.map((m) => (
          <ModuleCard
            key={m.index}
            projectId={projectId}
            module={m}
            busy={busy}
            expanded={open === m.index}
            onToggle={() => setOpen(open === m.index ? null : m.index)}
            onWrite={() => write(m.index)}
          />
        ))}
      </ol>

      {next && !busy && modules.length > 1 && (
        <p className="mt-4 text-sm text-[color:var(--muted)]">
          Next up: <span className="text-[color:var(--ink)]">{next.title}</span>
        </p>
      )}

      {error && (
        <p className="note note-bad mt-4 text-sm leading-6">{error}</p>
      )}
      </div>
    </section>
  );
}
