"use client";

// The plan screen: the whole plan, the last turn's report, and one free-text box.
//
// Ends at a document. Approval commits the decisions and hands them to the
// generator, which writes exactly what was approved -- so the plan is a promise
// the artifact keeps, rather than a screen the user passes through.

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api, type Commitment, type PlanView, type Sufficiency } from "@/lib/api";
import { compose } from "@/lib/compose";
import { PlanDocument } from "@/components/plan/PlanDocument";
import { Provenance } from "@/components/plan/Provenance";
import { TurnReport } from "@/components/plan/TurnReport";
import { CorrectionBox } from "@/components/plan/CorrectionBox";
import { Questions } from "@/components/plan/Questions";
import { GenerationPanel } from "@/components/plan/Generation";

export default function ProjectPage() {
  const { id } = useParams<{ id: string }>();
  const [view, setView] = useState<PlanView | null>(null);
  const [commitment, setCommitment] = useState<Commitment | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getPlan(id).then(setView).catch((e) => setError(String(e)));
  }, [id]);

  const correct = useCallback(
    async (text: string) => {
      setPending(true);
      setError(null);
      try {
        setView(await api.correct(id, text));
      } catch (e) {
        // The turn is lost; the conversation is not. Every earlier correction
        // is already persisted server-side.
        setError(
          `That turn failed: ${e instanceof Error ? e.message : String(e)}. ` +
            `Nothing else was lost — try again.`,
        );
      } finally {
        setPending(false);
      }
    },
    [id],
  );

  const skipQuestions = useCallback(async () => {
    setPending(true);
    setError(null);
    try {
      setView(await api.proceed(id));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setPending(false);
    }
  }, [id]);

  const approve = useCallback(async () => {
    setPending(true);
    setError(null);
    try {
      setCommitment(await api.approve(id));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setPending(false);
    }
  }, [id]);

  if (error && !view) {
    return <main className="mx-auto max-w-3xl p-10 text-sm text-red-800">{error}</main>;
  }
  if (!view) {
    return (
      <main className="mx-auto max-w-3xl p-10 text-sm text-[color:var(--muted)]">
        Loading the plan…
      </main>
    );
  }

  const changed = view.last_turn?.actual ?? [];
  // `asking` requires something to ask. A state that says "I'd rather ask than
  // guess" over an empty question list is a page with no control on it, which is
  // how a graph cheat-sheet request dead-ended. Belt and braces: the backend no
  // longer produces that state, and this cannot render it if it does.
  const asking = view.state === "asking" && view.questions.length > 0;
  const needsSubject = view.state === "needs_subject";
  const unplanned = !asking && !needsSubject && !view.decisions.scope;
  // Approval survives a reload; `commitment` only exists in the session that
  // clicked it. Reading both means coming back to an approved project shows the
  // document rather than asking you to approve it again.
  const approved = Boolean(commitment) || view.approved;
  // The backend sends {} until the first read completes.
  const sufficiency: Sufficiency | null =
    "verdict" in view.sufficiency ? (view.sufficiency as Sufficiency) : null;

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-3xl flex-col px-6 py-10">
      <a href="/" className="text-sm text-[color:var(--muted)] hover:underline">
        ← all projects
      </a>

      {(needsSubject || asking) && (
        <header className="mt-6">
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-[color:var(--muted)]">
            {needsSubject ? "What are we studying?" : "Reading your request"}
          </p>
          <h1 className="mt-3 text-3xl font-semibold tracking-tight text-[color:var(--ink)]">
            {view.decisions.interpret_situation?.subject ?? view.title}
          </h1>
          <p className="mt-2 text-sm leading-6 text-[color:var(--muted)]">
            {needsSubject
              ? "I couldn't tell what subject this is about, and there's nothing to plan without one."
              : "These would change the plan a lot, so I'd rather ask than guess."}
          </p>
        </header>
      )}

      {approved ? (
        <>
          <div className="mt-8 rounded-2xl border border-emerald-200 bg-emerald-50 p-6">
            <h2 className="text-lg font-semibold text-emerald-900">Plan approved</h2>
            <p className="mt-2 text-sm leading-6 text-emerald-900">
              {commitment
                ? `${commitment.decision_ids.length} decisions committed at ${commitment.approved_at}.`
                : "Committed earlier."}{" "}
              What gets written is what you just read.
            </p>
            <p className="mt-3 text-sm leading-6 text-emerald-900">
              A sample page to check the treatment before the whole thing is
              written would come next. <strong>That stage doesn&apos;t exist
              yet</strong> — for now this writes the whole document.
            </p>
          </div>
          <GenerationPanel projectId={id} />
        </>
      ) : null}

      {view.last_turn && !approved && (
        <div className="mt-8">
          <TurnReport turn={view.last_turn} />
        </div>
      )}

      {error && (
        <p className="mt-6 rounded-xl border border-red-200 bg-red-50 p-4 text-sm leading-6 text-red-800">
          {error}
        </p>
      )}

      {needsSubject && (
        <div className="mt-8 rounded-2xl border border-[color:var(--line)] bg-[color:var(--panel)] p-6">
          <p className="text-sm leading-6 text-[color:var(--muted)]">
            Tell me the subject and I&apos;ll take it from there. A topic is
            enough — I&apos;ll work out the rest and show you what I decided.
          </p>
          <div className="mt-4">
            <CorrectionBox
              onSubmit={correct}
              onApprove={() => {}}
              pending={pending}
              disabled={false}
              hideApprove
              label="What do you want to learn?"
            />
          </div>
        </div>
      )}

      {asking && (
        <div className="mt-8">
          <Questions
            questions={view.questions}
            onAnswer={correct}
            onSkip={skipQuestions}
            pending={pending}
          />
        </div>
      )}

      {unplanned && (
        <div className="mt-8 rounded-2xl border border-[color:var(--line)] bg-[color:var(--panel)] p-6">
          <h2 className="text-lg font-semibold tracking-tight text-[color:var(--ink)]">
            Nothing to ask
          </h2>
          <p className="mt-2 text-sm leading-6 text-[color:var(--muted)]">
            We read your request and there was nothing worth asking about — but
            the plan didn&apos;t get built. Nothing is lost; try again.
          </p>
          <button
            onClick={skipQuestions}
            disabled={pending}
            className="mt-4 rounded-full bg-[color:var(--ink)] px-5 py-2.5 text-sm font-medium text-white disabled:opacity-40"
          >
            {pending ? "Planning…" : "Plan it"}
          </button>
        </div>
      )}

      {!asking && !needsSubject && !unplanned && (
        <div className="mt-2 flex-1">
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-[color:var(--muted)]">
            The document we&apos;d make
          </p>
          <p className="mb-6 mt-2 text-sm leading-6 text-[color:var(--muted)]">
            Nothing is written yet. Read it and tell us what&apos;s wrong.
          </p>
          <PlanDocument
            doc={compose(
              view.decisions,
              view.extent,
              view.feasibility,
              sufficiency,
              view.title,
            )}
          />
          <Provenance decisions={view.decisions} sufficiency={sufficiency} />
        </div>
      )}

      {!approved && !asking && !needsSubject && !unplanned && (
        <CorrectionBox
          onSubmit={correct}
          onApprove={approve}
          pending={pending}
          disabled={false}
        />
      )}
    </main>
  );
}
