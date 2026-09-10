"use client";

// New project. One text box, one button.
//
// No level selector, no subject picker, no template chooser. Every one of those
// is a decision the system is supposed to make and then show as inferred
// (Semantics §3), and a template is never the user's to pick at all
// (Presentation-Boundary rule 1).

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, type ProjectSummary } from "@/lib/api";
import { ProjectRow } from "@/components/ProjectRow";
import { Spinner } from "@/components/ui/Spinner";

export default function Home() {
  const router = useRouter();
  const [text, setText] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [projects, setProjects] = useState<ProjectSummary[]>([]);

  useEffect(() => {
    api.listProjects().then(setProjects).catch(() => setProjects([]));
  }, []);

  async function submit() {
    if (text.trim().length < 3 || pending) return;
    setPending(true);
    setError(null);
    try {
      const view = await api.createProject(text.trim());
      router.push(`/projects/${view.project_id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setPending(false);
    }
  }

  const tooShort = text.trim().length < 3;

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-3xl flex-col justify-center px-6 py-16">
      <div className="flex items-center gap-2.5">
        <span
          aria-hidden
          className="h-2 w-2 rounded-full bg-[color:var(--accent)] shadow-[0_0_12px_var(--accent)]"
        />
        <span className="eyebrow">Study notes</span>
      </div>

      {/* The break is a typographic choice for the two-line desktop setting; at
          375px it fights the natural wrap and makes three ragged lines, so it
          only exists once there is room for it. */}
      <h1 className="mt-5 text-[2rem] font-semibold leading-[1.1] tracking-[-0.025em] text-[color:var(--ink)] sm:text-[2.75rem] sm:leading-[1.08]">
        What do you want
        <br className="hidden sm:inline" />{" "}
        to <span className="text-[color:var(--accent)]">learn</span>?
      </h1>

      <p className="mt-4 max-w-xl text-[0.9375rem] leading-7 text-[color:var(--muted)]">
        Say it however you like. We&apos;ll work out the rest and show you what we
        decided, before anything gets written.
      </p>

      <div className="panel panel-lift mt-9 p-2">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) submit();
          }}
          rows={4}
          disabled={pending}
          placeholder="i need to revise human evolution for NEET"
          className="w-full resize-none rounded-xl bg-transparent p-4 text-base leading-7 text-[color:var(--ink)] outline-none disabled:opacity-60"
        />
        <div className="flex flex-wrap items-center justify-between gap-3 px-2 pb-1.5 pt-1">
          <span className="font-[family-name:var(--font-mono)] text-[0.6875rem] tracking-wide text-[color:var(--soft)]">
            ⌘/Ctrl + ↵ to send
          </span>
          <button onClick={submit} disabled={pending || tooShort} className="btn btn-primary">
            {pending ? (
              <>
                <Spinner />
                Reading what you asked for…
              </>
            ) : (
              "Plan it"
            )}
          </button>
        </div>
      </div>

      {pending && (
        <p className="mt-4 text-sm leading-6 text-[color:var(--muted)]">
          This takes up to a minute. We&apos;re deciding scope, order and what to
          leave out.
        </p>
      )}

      {error && <p className="note note-bad mt-4 text-sm leading-6">{error}</p>}

      {projects.length > 0 && (
        <div className="mt-16 border-t border-[color:var(--line)] pt-8">
          <div className="flex flex-wrap items-baseline justify-between gap-x-4">
            <h2 className="eyebrow">Your projects</h2>
            <span className="font-[family-name:var(--font-mono)] text-[0.6875rem] tracking-wide text-[color:var(--soft)]">
              {projects.length}
            </span>
          </div>
          <ul className="mt-4 space-y-2">
            {projects.map((p) => (
              <ProjectRow key={p.id} project={p} />
            ))}
          </ul>
        </div>
      )}
    </main>
  );
}
