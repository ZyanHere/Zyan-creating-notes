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
import { Docket } from "@/components/plan/Docket";
import { PlanDocument } from "@/components/plan/PlanDocument";
import { PlanCaveats } from "@/components/plan/PlanCaveats";
import { Provenance } from "@/components/plan/Provenance";
import { TurnReport } from "@/components/plan/TurnReport";
import { CorrectionBox } from "@/components/plan/CorrectionBox";
import { Questions } from "@/components/plan/Questions";
import { Modules } from "@/components/plan/Modules";
import { Spinner } from "@/components/ui/Spinner";

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
    return (
      <main className="mx-auto max-w-3xl p-10">
        <p className="note note-bad text-sm leading-6">{error}</p>
      </main>
    );
  }
  if (!view) {
    return (
      <main className="mx-auto max-w-3xl p-10 text-sm text-[color:var(--muted)]">
        Loading the plan…
      </main>
    );
  }

  // `asking` requires something to ask. A state that says "I'd rather ask than
  // guess" over an empty question list is a page with no control on it, which is
  // how a graph cheat-sheet request dead-ended. Belt and braces: the backend no
  // longer produces that state, and this cannot render it if it does.
  const asking = view.state === "asking" && view.questions.length > 0;
  const needsSubject = view.state === "needs_subject";
  // Enough is known and no plan exists yet. The normal end of a conversation,
  // not a failure — planning costs minutes, so the user asks for it rather than
  // being charged for it by surprise.
  const ready = !asking && !needsSubject && !view.decisions.scope;
  // Approval survives a reload; `commitment` only exists in the session that
  // clicked it. Reading both means coming back to an approved project shows the
  // document rather than asking you to approve it again.
  const approved = Boolean(commitment) || view.approved;
  // The backend sends {} until the first read completes.
  const sufficiency: Sufficiency | null =
    "verdict" in view.sufficiency ? (view.sufficiency as Sufficiency) : null;
  const plan = compose(
    view.decisions,
    view.extent,
    view.feasibility,
    sufficiency,
    view.title,
  );

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-4xl flex-col px-6 py-10">
      <Docket
        id={id}
        title={view.decisions.interpret_situation?.subject ?? view.title}
        state={view.state}
        approved={approved}
      />

      {(needsSubject || asking) && (
        <div className="margined mt-12">
          <p className="rail">{needsSubject ? "Subject" : "Intake"}</p>
          <header>
            <h1 className="font-[family-name:var(--font-serif)] text-[1.75rem] font-normal leading-[1.2] tracking-[-0.01em] text-[color:var(--ink)]">
              {view.decisions.interpret_situation?.subject ?? view.title}
            </h1>
            <p className="mt-2 max-w-[54ch] text-sm leading-6 text-[color:var(--muted)]">
              {needsSubject
                ? "I couldn't tell what subject this is about, and there's nothing to plan without one."
                : "A few things would change the plan enough that guessing them would waste your time."}
            </p>
          </header>
        </div>
      )}

      {approved ? (
        <>
          {/* The stamp. The app's one piece of overt visual personality, and
              it is placed where something genuinely was signed off. */}
          <div className="margined mt-12">
            <p className="rail">Signed off</p>
            <div className="flex flex-wrap items-baseline gap-x-4 gap-y-2">
              <span className="stamp">
                Approved
                {commitment && (
                  <span className="opacity-60">
                    · committed {commitment.decision_ids.length} decisions
                  </span>
                )}
              </span>
              <span className="text-sm text-[color:var(--muted)]">
                What gets printed is what you approved.
              </span>
            </div>
          </div>

          <Modules projectId={id} />

          {/* The plan does not disappear when it is approved -- it stops being
              the page. Its contents are on the module cards now, where they are
              acted on; what is left here is the part that belongs to no single
              module, kept for reference rather than re-read every visit. */}
          <details className="mt-10 border-t border-[color:var(--line)] pt-5">
            <summary className="group inline-flex cursor-pointer items-center gap-2 text-sm text-[color:var(--muted)] transition-colors hover:text-[color:var(--accent)]">
              <span
                aria-hidden
                className="text-[0.625rem] transition-transform group-open:rotate-90"
              >
                ▶
              </span>
              What you approved
            </summary>
            <div className="mt-1">
              <PlanCaveats doc={plan} />
              <p className="mt-8 text-sm leading-6 text-[color:var(--muted)]">
                A sample page to check the treatment before anything is written
                would come next. <strong>That stage doesn&apos;t exist yet.</strong>
              </p>
              <Provenance decisions={view.decisions} sufficiency={sufficiency} />
            </div>
          </details>
        </>
      ) : null}

      {view.last_turn && !approved && (
        <div className="mt-8">
          <TurnReport turn={view.last_turn} />
        </div>
      )}

      {error && (
        <p className="note note-bad mt-6 text-sm leading-6">{error}</p>
      )}

      {needsSubject && (
        <div className="sheet mt-8 p-6">
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
              embedded
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

      {ready && (
        <div className="sheet mt-8 p-6">
          <h2 className="text-lg font-semibold tracking-[-0.01em] text-[color:var(--ink)]">
            Ready to plan
          </h2>
          <p className="mt-2 text-sm leading-6 text-[color:var(--muted)]">
            Here&apos;s what we understood. Building the plan takes a few
            minutes — working out what exists, what&apos;s relevant to you, and
            how it divides.
          </p>

          {view.decisions.interpret_situation && (
            <dl className="mt-5 space-y-3 border-l-2 border-[color:var(--accent-line)] pl-4">
              {(
                [
                  ["Subject", view.decisions.interpret_situation.subject],
                  ["Why you want it", view.decisions.interpret_situation.purpose],
                  ["What you already know", view.decisions.interpret_situation.entry_point],
                  ["By the end", view.decisions.interpret_situation.target_capability],
                ] as [string, string | undefined][]
              )
                .filter(([, value]) => Boolean(value))
                .map(([label, value]) => (
                  <div key={label}>
                    <dt className="eyebrow text-[0.625rem]">{label}</dt>
                    <dd className="mt-0.5 text-sm leading-6 text-[color:var(--ink)]">{value}</dd>
                  </div>
                ))}
            </dl>
          )}

          <div className="mt-5 flex flex-wrap items-center gap-3">
            <button onClick={skipQuestions} disabled={pending} className="btn btn-primary">
              {pending ? (
                <>
                  <Spinner />
                  Planning…
                </>
              ) : (
                "Build the plan"
              )}
            </button>
            {pending && (
              <span className="text-sm text-[color:var(--muted)]">
                deriving the curriculum · a few minutes · nothing is written yet
              </span>
            )}
          </div>

          <p className="mt-4 text-sm leading-6 text-[color:var(--muted)]">
            Anything wrong above? Tell us below and we&apos;ll re-read it first.
          </p>
          <div className="mt-3">
            <CorrectionBox
              onSubmit={correct}
              onApprove={() => {}}
              pending={pending}
              disabled={false}
              hideApprove
              embedded
              label="Anything we got wrong?"
            />
          </div>
        </div>
      )}

      {!asking && !needsSubject && !ready && !approved && (
        <div className="mt-2 flex-1">
          <p className="eyebrow eyebrow-accent">The proof</p>
          <p className="mt-2 max-w-[54ch] text-sm leading-6 text-[color:var(--muted)]">
            Nothing has been written yet. This is the part where you get to
            disagree — say what&apos;s wrong below and I&apos;ll re-plan it.
          </p>
          {/* This screen's aside is about the thing that made this screen. The
              planner is genuinely the weakest link — it is one pass from a free
              model over a concept graph — and the correction box exists because
              of that, so saying so is honest and points at the fix. */}
          <p className="aside mb-6 mt-3 max-w-[54ch]">
            the planner is the weak link right now — one pass, free model. if this
            reads wrong, the box at the bottom is the actual fix. rewriting it.
          </p>
          <PlanDocument doc={plan} />
          <Provenance decisions={view.decisions} sufficiency={sufficiency} />
        </div>
      )}

      {!approved && !asking && !needsSubject && !ready && (
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
