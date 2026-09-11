"use client";

// The decider's questions, one at a time, answered in a single turn.
//
// SERIALISED IN PRESENTATION, NOT IN CONVERSATION. The axes are independent —
// why you want it does not depend on what you already know — so asking them as
// three round trips would buy nothing and cost two extra model calls. This asks
// them one at a time and submits every answer together, so the turn count is
// still one. One card with one question is a decision; three stacked cards with
// eleven options between them is a form, and a form is the thing people abandon.
//
// Objective, not open-ended: Semantics §1 says the learner cannot reliably
// *specify* their entry point or target, but can *recognise* their situation
// when it is put in front of them. So each question offers recognisable options
// — and every one of them also carries a free-text row, because the option list
// is the system's guess at the shape of the answer and sometimes that guess is
// wrong. "Skip" and "use the defaults" stay available throughout: §3 makes a
// question an offer to correct early, never a gate.

import { useCallback, useEffect, useState } from "react";
import type { Question } from "@/lib/api";
import { axisName } from "@/lib/compose";
import { Spinner } from "@/components/ui/Spinner";

export function Questions({
  questions,
  onAnswer,
  onSkip,
  pending,
}: {
  questions: Question[];
  onAnswer: (text: string) => void;
  onSkip: () => void;
  pending: boolean;
}) {
  // `at === questions.length` is the review step, not a question.
  const [at, setAt] = useState(0);
  const [picked, setPicked] = useState<Record<string, string>>({});
  const [custom, setCustom] = useState<Record<string, string>>({});

  const total = questions.length;
  const reviewing = at >= total;
  const q = reviewing ? null : questions[at];

  const answerFor = useCallback(
    (axis: string) => custom[axis]?.trim() || picked[axis] || null,
    [custom, picked],
  );

  const go = useCallback(
    (to: number) => setAt(Math.max(0, Math.min(total, to))),
    [total],
  );

  const choose = useCallback(
    (axis: string, label: string) => {
      if (pending) return;
      // Picking from the list retracts anything typed for the same axis --
      // otherwise the free text would silently win while the highlighted row
      // said something else.
      setPicked((p) => ({ ...p, [axis]: label }));
      setCustom((c) => ({ ...c, [axis]: "" }));
      setAt((i) => i + 1);
    },
    [pending],
  );

  // Number keys pick an option. The numerals beside each row are a promise that
  // this works; without the handler they are decoration that reads as one.
  useEffect(() => {
    if (!q || pending) return;
    const options = q.options;
    const axis = q.axis;
    function onKey(event: KeyboardEvent) {
      const el = document.activeElement;
      if (el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement) return;
      const n = Number(event.key);
      if (Number.isInteger(n) && n >= 1 && n <= options.length) {
        event.preventDefault();
        choose(axis, options[n - 1].label);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [q, pending, choose]);

  if (total === 0) return null;

  function submit() {
    if (pending) return;
    // The answer is testimony, so it is written the way a person would say it
    // rather than as a form payload.
    const lines = questions
      .map((x) => {
        const said = answerFor(x.axis);
        return said ? `${axisName(x.axis)}: ${said}` : null;
      })
      .filter((line): line is string => line !== null);
    // Skipping every question is a real choice, and it is exactly the one
    // "use the defaults" makes. Sending an empty correction instead would be a
    // live-looking button that does nothing -- which is what this did first.
    if (lines.length === 0) onSkip();
    else onAnswer(lines.join("\n"));
  }

  if (reviewing) {
    const answered = questions.filter((x) => answerFor(x.axis)).length;
    return (
      <section className="sheet overflow-hidden">
        <header className="flex flex-wrap items-center justify-between gap-3 border-b border-[color:var(--line)] px-5 py-4">
          <h2 className="font-[family-name:var(--font-serif)] text-[1.0625rem] text-[color:var(--ink)]">
            {answered === total ? "That's everything" : `${answered} of ${total} answered`}
          </h2>
          <span className="font-[family-name:var(--font-mono)] text-[0.6875rem] uppercase tracking-wider text-[color:var(--soft)]">
            Change anything before we plan
          </span>
        </header>

        <ul>
          {questions.map((x, i) => {
            const said = answerFor(x.axis);
            return (
              <li
                key={x.axis}
                className="flex items-baseline gap-3 border-b border-[color:var(--line)] px-5 py-3"
              >
                <span className="font-[family-name:var(--font-mono)] text-[0.6875rem] tabular-nums text-[color:var(--soft)]">
                  {i + 1}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="text-sm text-[color:var(--muted)]">{x.question}</p>
                  <p
                    className={`text-sm leading-6 ${
                      said ? "text-[color:var(--ink)]" : "italic text-[color:var(--soft)]"
                    }`}
                  >
                    {said ?? "skipped — we'll use the default"}
                  </p>
                </div>
                <button
                  onClick={() => go(i)}
                  disabled={pending}
                  className="shrink-0 text-sm text-[color:var(--muted)] underline decoration-[color:var(--line-strong)] underline-offset-4 transition-colors hover:text-[color:var(--accent)] disabled:opacity-40"
                >
                  Change
                </button>
              </li>
            );
          })}
        </ul>

        <div className="flex flex-wrap items-center gap-3 px-5 py-4">
          <button onClick={submit} disabled={pending} className="btn btn-primary">
            {pending ? (
              <>
                <Spinner />
                Planning…
              </>
            ) : (
              "Plan it"
            )}
          </button>
          {pending ? (
            <span className="text-sm text-[color:var(--muted)]">
              deriving the curriculum · up to a minute
            </span>
          ) : (
            <button
              onClick={onSkip}
              className="text-sm text-[color:var(--muted)] underline decoration-[color:var(--line-strong)] underline-offset-4 transition-colors hover:text-[color:var(--accent)]"
            >
              Use the defaults instead
            </button>
          )}
        </div>
      </section>
    );
  }

  const axis = q!.axis;
  const typed = custom[axis] ?? "";

  function commitTyped() {
    if (pending || !typed.trim()) return;
    // Typing wins over any earlier pick on this axis, and `answerFor` already
    // prefers it -- clearing the pick keeps the review step honest.
    setPicked((p) => ({ ...p, [axis]: "" }));
    setAt((i) => i + 1);
  }

  return (
    <section className="sheet overflow-hidden">
      {/* The pager takes its own row below 640px. Beside a question that wraps
          to three lines it reads as though it belongs to the last of them. */}
      <header className="flex flex-col gap-1.5 border-b border-[color:var(--line)] px-5 py-4 sm:flex-row sm:items-start sm:justify-between sm:gap-4">
        <div className="min-w-0 sm:order-first">
          <h2 className="font-[family-name:var(--font-serif)] text-[1.0625rem] leading-6 text-[color:var(--ink)]">
            {q!.question}
          </h2>
          {q!.why_it_matters && (
            <p className="mt-1 text-sm leading-6 text-[color:var(--muted)]">
              {q!.why_it_matters}
            </p>
          )}
        </div>

        <nav
          className="order-first flex shrink-0 items-center gap-0.5 self-end sm:order-none sm:self-auto"
          aria-label="Questions"
        >
          <Step
            label="Previous question"
            glyph="‹"
            onClick={() => go(at - 1)}
            disabled={pending || at === 0}
          />
          <span className="px-1 font-[family-name:var(--font-mono)] text-[0.6875rem] tabular-nums text-[color:var(--muted)]">
            {at + 1} of {total}
          </span>
          <Step
            label="Next question"
            glyph="›"
            onClick={() => go(at + 1)}
            disabled={pending}
          />
          <Step
            label="Skip all — use the defaults"
            glyph="✕"
            onClick={onSkip}
            disabled={pending}
            className="ml-1"
          />
        </nav>
      </header>

      <ul>
        {q!.options.map((o, k) => {
          const on = picked[axis] === o.label && !typed.trim();
          return (
            <li key={o.label}>
              <button
                disabled={pending}
                onClick={() => choose(axis, o.label)}
                className={`group flex w-full items-start gap-3 border-b border-l-2 border-b-[color:var(--line)] px-5 py-3.5 text-left transition-colors disabled:opacity-50 ${
                  on
                    ? "border-l-[color:var(--accent)] bg-[color:var(--accent-bg)]"
                    : "border-l-transparent hover:bg-[color:var(--panel-strong)]"
                }`}
              >
                <span
                  aria-hidden
                  className={`w-5 shrink-0 pt-1 font-[family-name:var(--font-mono)] text-[0.6875rem] tabular-nums transition-colors ${
                    on
                      ? "text-[color:var(--accent)]"
                      : "text-[color:var(--soft)] group-hover:text-[color:var(--accent)]"
                  }`}
                >
                  {k + 1}
                </span>

                <span className="min-w-0 flex-1">
                  <span className="flex flex-wrap items-baseline gap-x-2">
                    <span className="font-[family-name:var(--font-serif)] text-[0.9375rem] text-[color:var(--ink)]">
                      {o.label}
                    </span>
                    {o.label === q!.default_label && (
                      <span className="font-[family-name:var(--font-mono)] text-[0.625rem] uppercase tracking-wider text-[color:var(--soft)]">
                        default
                      </span>
                    )}
                  </span>
                  {o.implication && (
                    <span className="mt-0.5 block text-sm leading-6 text-[color:var(--muted)]">
                      {o.implication}
                    </span>
                  )}
                </span>

                <span
                  aria-hidden
                  className={`shrink-0 pt-0.5 transition-all ${
                    on
                      ? "text-[color:var(--accent)]"
                      : "text-[color:var(--soft)] opacity-0 group-hover:translate-x-0.5 group-hover:opacity-100"
                  }`}
                >
                  →
                </span>
              </button>
            </li>
          );
        })}
      </ul>

      {/* The row that is on every question. The options are the system's guess
          at the shape of the answer; this is where the guess being wrong stops
          being the user's problem. */}
      <div className="flex items-center gap-3 px-5 py-3">
        <span
          aria-hidden
          className={`w-5 shrink-0 text-[0.6875rem] transition-colors ${
            typed.trim() ? "text-[color:var(--accent)]" : "text-[color:var(--soft)]"
          }`}
        >
          ✎
        </span>
        <input
          value={typed}
          onChange={(e) => setCustom((c) => ({ ...c, [axis]: e.target.value }))}
          onKeyDown={(e) => {
            if (e.key === "Enter") commitTyped();
          }}
          disabled={pending}
          placeholder="Something else"
          aria-label="Answer in your own words"
          className="min-w-0 flex-1 bg-transparent font-[family-name:var(--font-serif)] text-[0.9375rem] text-[color:var(--ink)] outline-none placeholder:text-[color:var(--soft)] placeholder:italic disabled:opacity-50"
        />
        <button
          onClick={typed.trim() ? commitTyped : () => go(at + 1)}
          disabled={pending}
          className="btn btn-ghost shrink-0"
        >
          {typed.trim() ? "Save" : "Skip"}
        </button>
      </div>
    </section>
  );
}

function Step({
  label,
  glyph,
  onClick,
  disabled,
  className = "",
}: {
  label: string;
  glyph: string;
  onClick: () => void;
  disabled: boolean;
  className?: string;
}) {
  return (
    <button
      type="button"
      title={label}
      aria-label={label}
      onClick={onClick}
      disabled={disabled}
      className={`grid h-6 w-6 place-items-center rounded-md text-sm text-[color:var(--muted)] transition-colors hover:bg-[color:var(--panel-strong)] hover:text-[color:var(--accent)] disabled:pointer-events-none disabled:opacity-30 ${className}`}
    >
      {glyph}
    </button>
  );
}
