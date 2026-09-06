"use client";

// New project. One text box, one button.
//
// No level selector, no subject picker, no template chooser. Every one of those
// is a decision the system is supposed to make and then show as inferred
// (Semantics §3), and a template is never the user's to pick at all
// (Presentation-Boundary rule 1).

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

export default function Home() {
  const router = useRouter();
  const [text, setText] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [projects, setProjects] = useState<{ id: string; title: string }[]>([]);

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

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-3xl flex-col justify-center px-6 py-16">
      <p className="text-xs font-semibold uppercase tracking-[0.28em] text-[color:var(--muted)]">
        Study notes
      </p>
      <h1 className="mt-3 text-4xl font-semibold tracking-tight text-[color:var(--ink)]">
        What do you want to learn?
      </h1>
      <p className="mt-3 text-sm leading-6 text-[color:var(--muted)]">
        Say it however you like. We&apos;ll work out the rest and show you what we
        decided, before anything gets written.
      </p>

      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) submit();
        }}
        rows={4}
        disabled={pending}
        placeholder="i need to revise human evolution for NEET"
        className="mt-8 w-full resize-none rounded-2xl border border-[color:var(--line)] bg-[color:var(--panel)] p-5 text-base leading-7 text-[color:var(--ink)] outline-none placeholder:text-[color:var(--muted)]/60 focus:border-[color:var(--line-strong)] disabled:opacity-60"
      />

      <div className="mt-4 flex items-center gap-4">
        <button
          onClick={submit}
          disabled={pending || text.trim().length < 3}
          className="rounded-full bg-[color:var(--ink)] px-6 py-3 text-sm font-medium text-white disabled:opacity-40"
        >
          {pending ? "Reading what you asked for…" : "Plan it"}
        </button>
        {pending && (
          <span className="text-sm text-[color:var(--muted)]">
            This takes up to a minute. We&apos;re deciding scope, order and what to
            leave out.
          </span>
        )}
      </div>

      {error && (
        <p className="mt-4 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          {error}
        </p>
      )}

      {projects.length > 0 && (
        <div className="mt-16 border-t border-[color:var(--line)] pt-8">
          <h2 className="text-xs font-semibold uppercase tracking-[0.28em] text-[color:var(--muted)]">
            Earlier
          </h2>
          <ul className="mt-4 space-y-2">
            {projects.map((p) => (
              <li key={p.id}>
                <a
                  href={`/projects/${p.id}`}
                  className="block rounded-xl border border-[color:var(--line)] bg-[color:var(--panel-soft)] px-4 py-3 text-sm text-[color:var(--ink)] hover:border-[color:var(--line-strong)]"
                >
                  {p.title}
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}
    </main>
  );
}
