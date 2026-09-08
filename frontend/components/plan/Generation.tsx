"use client";

// What happens after approval: the document gets written, and you watch it.
//
// This replaces a dead end. The approved state used to say "that stage doesn't
// exist yet — this is where the build currently stops," which was true: the plan
// gate wrote a commitment nothing downstream read.
//
// Polled rather than awaited. Generation is a model call plus a browser render,
// minutes on the free tier, and it has come back empty — a fetch held open for
// that fails as a dead socket with nothing said about why.

import { useCallback, useEffect, useRef, useState } from "react";
import { api, artifactUrl, type Generation } from "@/lib/api";
import { FulfilmentReport } from "@/components/plan/Fulfilment";

const POLL_MS = 2500;

export function GenerationPanel({ projectId }: { projectId: string }) {
  const [gen, setGen] = useState<Generation | null>(null);
  const [error, setError] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const poll = useCallback(async () => {
    try {
      const next = await api.getGeneration(projectId);
      setGen(next);
      if (next.state === "running") {
        timer.current = setTimeout(poll, POLL_MS);
      }
    } catch (e) {
      // A failed poll is not a failed generation — the work continues on the
      // server. Say so rather than implying the document was lost.
      setError(
        `Lost contact while waiting: ${e instanceof Error ? e.message : String(e)}. ` +
          `The document may still be writing — reload to check.`,
      );
    }
  }, [projectId]);

  useEffect(() => {
    poll();
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, [poll]);

  const start = useCallback(async () => {
    setError(null);
    setGen({ state: "running" });
    try {
      await api.startGeneration(projectId);
      poll();
    } catch (e) {
      setGen(null);
      setError(e instanceof Error ? e.message : String(e));
    }
  }, [projectId, poll]);

  const state = gen?.state ?? "idle";

  return (
    <section className="mt-6 rounded-2xl border border-[color:var(--line)] bg-[color:var(--panel)] p-6">
      <h2 className="text-lg font-semibold tracking-tight text-[color:var(--ink)]">
        {state === "done"
          ? gen?.satisfied === false
            ? "Your document — incomplete"
            : "Your document"
          : "Write the document"}
      </h2>

      {state === "idle" && (
        <>
          <p className="mt-2 text-sm leading-6 text-[color:var(--muted)]">
            Everything above is what gets written — the same concepts, the same
            order, the same depths. It takes a few minutes.
          </p>
          <button
            onClick={start}
            className="mt-4 rounded-full bg-[color:var(--ink)] px-5 py-2.5 text-sm font-medium text-white"
          >
            Write it
          </button>
        </>
      )}

      {state === "running" && (
        <p className="mt-2 text-sm leading-6 text-[color:var(--muted)]">
          Writing
          {typeof gen?.seconds === "number" ? ` — ${Math.round(gen.seconds)}s so far` : "…"}.
          This takes a few minutes and it is safe to leave this page; the work
          carries on without you.
        </p>
      )}

      {state === "failed" && (
        <>
          <p className="mt-2 text-sm leading-6 text-red-800">
            The document didn&apos;t get written: {gen?.error}
          </p>
          <p className="mt-2 text-sm leading-6 text-[color:var(--muted)]">
            Your approved plan is untouched. Nothing was lost but the attempt.
          </p>
          <button
            onClick={start}
            className="mt-4 rounded-full bg-[color:var(--ink)] px-5 py-2.5 text-sm font-medium text-white"
          >
            Try again
          </button>
        </>
      )}

      {state === "done" && gen && (
        <>
          <p className="mt-2 text-sm leading-6 text-[color:var(--muted)]">
            {gen.title}
            {gen.pages ? ` · ${gen.pages} page${gen.pages === 1 ? "" : "s"}` : ""}
            {gen.calls ? ` · written in ${gen.calls} passes` : ""}
          </p>

          {gen.fulfilment && <FulfilmentReport report={gen.fulfilment} />}

          <div className="mt-4 flex flex-wrap gap-3">
            <a
              href={artifactUrl(projectId)}
              target="_blank"
              rel="noreferrer"
              className="rounded-full bg-[color:var(--ink)] px-5 py-2.5 text-sm font-medium text-white"
            >
              Open in a new tab
            </a>
            <a
              href={artifactUrl(projectId, true)}
              className="rounded-full border border-[color:var(--line)] px-5 py-2.5 text-sm text-[color:var(--ink)]"
            >
              Download
            </a>
            <button
              onClick={start}
              className="rounded-full border border-[color:var(--line)] px-5 py-2.5 text-sm text-[color:var(--ink)]"
            >
              Write it again
            </button>
          </div>

          <object
            data={artifactUrl(projectId)}
            type="application/pdf"
            className="mt-5 h-[36rem] w-full rounded-xl border border-[color:var(--line)]"
          >
            <p className="p-4 text-sm text-[color:var(--muted)]">
              Your browser won&apos;t preview PDFs inline —{" "}
              <a className="underline" href={artifactUrl(projectId)}>
                open it in a new tab
              </a>
              .
            </p>
          </object>

          {/* Not a debug panel. A figure the document needed and we cannot draw
              is something the reader is owed, and burying it here would be the
              quiet omission the whole representation layer exists to prevent. */}
          {gen.representation?.stated_gaps?.length ? (
            <div className="mt-5 rounded-xl border border-[color:var(--line)] bg-[color:var(--panel-soft)] p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[color:var(--muted)]">
                Figures we couldn&apos;t draw
              </p>
              <ul className="mt-2 space-y-1.5">
                {gen.representation.stated_gaps.map((gap) => (
                  <li key={gap} className="text-sm leading-6 text-[color:var(--soft)]">
                    {gap}
                  </li>
                ))}
              </ul>
              <p className="mt-2 text-sm leading-6 text-[color:var(--muted)]">
                Each is marked in the document, with what the figure would have
                had to show.
              </p>
            </div>
          ) : null}

          {gen.representation?.unrendered?.length ? (
            <p className="mt-4 text-sm leading-6 text-red-800">
              The design couldn&apos;t draw {gen.representation.unrendered.join(", ")}.
              Those blocks are missing from the PDF — this is a bug, not a choice.
            </p>
          ) : null}
        </>
      )}

      {error && (
        <p className="mt-4 rounded-xl border border-red-200 bg-red-50 p-4 text-sm leading-6 text-red-800">
          {error}
        </p>
      )}
    </section>
  );
}
