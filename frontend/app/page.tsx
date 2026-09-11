"use client";

// The commission desk.
//
// Not a chat box. You are not asking a question and getting an answer — you
// are commissioning a document and will be shown the spec before anything is
// written. The page is laid out as numbered sections of a printed manual:
// §01 you place the order, §02 is the archive of orders already placed.
//
// No level selector, no subject picker, no template chooser. Every one of
// those is a decision the system is supposed to make and then show as inferred
// (Semantics §3), and a template is never the user's to pick at all
// (Presentation-Boundary rule 1).
//
// Nothing on this page is a prop: every control does something. The design
// this was built from also had an attachment button, a per-card overflow menu
// and a "How it works" link — all three were dropped rather than shipped
// inert, because the API has no attachment field, no rename and no delete.

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { api, type ProjectSummary } from "@/lib/api";
import { ProjectCard } from "@/components/ProjectCard";
import { HeroAnnotation } from "@/components/HeroAnnotation";
import { Spinner } from "@/components/ui/Spinner";

/** Loaded into the box on click. Real subjects this has actually planned — an
 *  example that fails is worse than no example. */
const EXAMPLES = [
  "Agentic AI",
  "Transformer architecture",
  "System design",
  "Human evolution",
  "Arrays (DSA)",
];

/** How much of the archive the grid shows. Six fills two rows of three and
 *  keeps the first screen about commissioning rather than browsing. */
const RECENT = 6;

export default function Home() {
  const router = useRouter();
  const [text, setText] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [projects, setProjects] = useState<ProjectSummary[] | null>(null);
  const [showAll, setShowAll] = useState(false);
  const box = useRef<HTMLTextAreaElement>(null);

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

  function loadExample(topic: string) {
    setText(topic);
    box.current?.focus();
  }

  const tooShort = text.trim().length < 3;
  const shown = projects ? (showAll ? projects : projects.slice(0, RECENT)) : [];

  return (
    <>
      <nav className="sticky top-0 z-20 border-b border-[color:var(--line)] bg-[color:var(--canvas)]/90 backdrop-blur-xl">
        <div className="mx-auto flex max-w-[68rem] flex-wrap items-center gap-x-8 gap-y-2 px-6 py-4">
          <span className="font-[family-name:var(--font-mono)] text-sm font-semibold tracking-[0.2em] text-[color:var(--ink)]">
            MY<span className="text-[color:var(--accent)]">NOTES</span>
          </span>
          <div className="flex items-center gap-6 text-sm">
            <span
              aria-current="page"
              className="border-b-2 border-[color:var(--accent)] pb-0.5 text-[color:var(--ink)]"
            >
              Home
            </span>
            <a
              href="#archive"
              className="pb-0.5 text-[color:var(--muted)] transition-colors hover:text-[color:var(--accent)]"
            >
              Archive
            </a>
          </div>
          <span className="eyebrow ml-auto hidden lg:inline">
            study notes, printed to order
          </span>
        </div>
      </nav>

      <main className="mx-auto w-full max-w-[68rem] px-6 pb-24">
        {/* ---- §01 the commission -------------------------------------- */}
        <section className="pt-14">
          <div className="flex items-start gap-x-10">
            <div className="min-w-0 flex-1">
              <p className="marker">
                01 <span aria-hidden className="marker-rule" />
              </p>
              <p className="mt-4 font-[family-name:var(--font-mono)] text-[0.6875rem] uppercase leading-6 tracking-[0.14em] text-[color:var(--muted)]">
                A small publishing studio.
                <br />
                For curious people.
              </p>

              <h1 className="mt-8 font-[family-name:var(--font-serif)] text-[2.4rem] font-normal leading-[1.12] tracking-[-0.015em] text-[color:var(--ink)] sm:text-[3.2rem]">
                You bring the topic.
                <br />
                I&apos;ll handle the{" "}
                <span className="text-[color:var(--accent)]">rest.</span>
                <span className="caret" aria-hidden />
              </h1>

              <p className="mt-6 max-w-[52ch] font-[family-name:var(--font-serif)] text-[1.0625rem] leading-8 text-[color:var(--muted)]">
                I&apos;ll figure out the structure, break it into modules, and
                generate complete, clean notes — you just tell me the goal.
              </p>
            </div>

            {/* Margin annotation. Decorative, so it goes when there is no
                margin to put it in. */}
            <div className="hidden shrink-0 pt-16 lg:block">
              <HeroAnnotation />
            </div>
          </div>

          <div className="sheet-soft mt-10 p-2">
            <textarea
              ref={box}
              value={text}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) submit();
              }}
              rows={4}
              disabled={pending}
              placeholder={
                'e.g. "I want to learn about agentic AI for real-world applications…"'
              }
              aria-label="What do you want to learn?"
              className="w-full resize-none bg-transparent px-4 py-3 font-[family-name:var(--font-serif)] text-[1.0625rem] leading-8 text-[color:var(--ink)] outline-none placeholder:italic placeholder:text-[color:var(--soft)] disabled:opacity-60"
            />
            <div className="flex flex-wrap items-center justify-end gap-x-4 gap-y-2 px-2 pb-1 pt-1">
              <span className="font-[family-name:var(--font-mono)] text-[0.6875rem] text-[color:var(--soft)]">
                {pending ? "first inference pass · 20–60s" : "Ctrl + ↵ to start"}
              </span>
              <button
                onClick={submit}
                disabled={pending || tooShort}
                className="btn btn-primary"
              >
                {pending ? (
                  <>
                    <Spinner />
                    Reading it
                  </>
                ) : (
                  <>
                    Start commission <span aria-hidden>→</span>
                  </>
                )}
              </button>
            </div>
          </div>

          <div className="mt-5 flex flex-wrap items-center gap-2.5">
            <span className="eyebrow mr-1">Example topics</span>
            {EXAMPLES.map((topic) => (
              <button key={topic} onClick={() => loadExample(topic)} className="chip">
                {topic}
              </button>
            ))}
          </div>

          {/* Home's aside: what you are commissioning from. Beside the slip,
              not in a footer, because it is about the request you are about to
              make. */}
          <p className="aside mt-6 max-w-[58ch]">
            solo project, free inference tier, no budget. it will be slower than you
            want. hire me <span aria-hidden>🫡</span>
          </p>

          {error && <p className="note note-bad mt-6 text-sm leading-6">{error}</p>}
        </section>

        {/* ---- §02 the archive ----------------------------------------- */}
        <section id="archive" className="mt-24 scroll-mt-24 border-t border-[color:var(--line)] pt-12">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="marker">
                <span className="text-[color:var(--accent)]">02</span>
                <span aria-hidden className="marker-rule" />
                <span>Your archive</span>
              </p>
              <h2 className="mt-3 font-[family-name:var(--font-serif)] text-[1.9rem] font-normal leading-tight text-[color:var(--ink)]">
                Previous commissions
              </h2>
              <p className="mt-1.5 font-[family-name:var(--font-mono)] text-[0.75rem] text-[color:var(--muted)]">
                Pick up where you left off.
              </p>
            </div>
            <button
              onClick={() => box.current?.focus()}
              className="font-[family-name:var(--font-mono)] text-[0.75rem] text-[color:var(--accent)] underline decoration-[color:var(--accent-line)] underline-offset-4 transition-colors hover:decoration-current"
            >
              + New commission
            </button>
          </div>

          {projects === null ? (
            <p className="mt-8 font-[family-name:var(--font-mono)] text-xs text-[color:var(--soft)]">
              loading…
            </p>
          ) : projects.length === 0 ? (
            <p className="mt-8 max-w-[54ch] text-sm leading-6 text-[color:var(--muted)]">
              Nothing commissioned yet. Whatever you type above becomes a project you
              can come back to — the plan, the modules and the PDFs all stay with it.
            </p>
          ) : (
            <>
              <ul className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {shown.map((p) => (
                  <ProjectCard key={p.id} project={p} />
                ))}
              </ul>
              {projects.length > RECENT && (
                <button
                  onClick={() => setShowAll((v) => !v)}
                  className="mt-6 font-[family-name:var(--font-mono)] text-[0.75rem] text-[color:var(--muted)] underline decoration-[color:var(--line-strong)] underline-offset-4 transition-colors hover:text-[color:var(--accent)]"
                >
                  {showAll ? "Show recent only" : `Show all ${projects.length} commissions`}
                </button>
              )}
            </>
          )}
        </section>
      </main>

      <footer className="border-t border-[color:var(--line)]">
        <div className="mx-auto flex max-w-[68rem] flex-wrap items-center gap-x-8 gap-y-4 px-6 py-8">
          <span className="font-[family-name:var(--font-mono)] text-sm font-semibold tracking-[0.2em] text-[color:var(--ink)]">
            MY<span className="text-[color:var(--accent)]">NOTES</span>
          </span>
          <span className="font-[family-name:var(--font-mono)] text-[0.6875rem] text-[color:var(--soft)]">
            v{process.env.NEXT_PUBLIC_APP_VERSION} · a work in progress
          </span>

          {/* Engineering status: standing facts about the build. Not an aside —
              the self-aware notes live next to the things they are about. */}
          <div className="ml-auto font-[family-name:var(--font-mono)] text-[0.6875rem] leading-5 text-[color:var(--soft)] sm:border-l sm:border-[color:var(--line)] sm:pl-8">
            <p>built by one person, for people who like to learn</p>
            <p>authentication deliberately skipped for now · work in progress</p>
          </div>
        </div>
      </footer>
    </>
  );
}
