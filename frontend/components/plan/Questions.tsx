"use client";

// Every question the decider chose, on one screen.
//
// The axes are independent — why you want it does not depend on what you
// already know — so serialising them buys nothing and costs turns. The goal is
// planning sufficiency in the fewest conversational turns, and one screen of
// three choices is one turn.
//
// Objective, not open-ended: Semantics §1 says the learner cannot reliably
// *specify* their entry point or target, but can *recognise* their situation
// when it is put in front of them. "Something else" and "plan it anyway" are
// always available — §3 makes a question an offer to correct early, never a gate.

import { useState } from "react";
import type { Question } from "@/lib/api";
import { axisName } from "@/lib/compose";

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
  const [picked, setPicked] = useState<Record<string, string>>({});
  const [other, setOther] = useState("");

  if (questions.length === 0) return null;

  const answered = questions.filter((q) => picked[q.axis]).length;

  function send() {
    if (pending) return;
    // The answer is testimony, so it is written the way a person would say it
    // rather than as a form payload.
    const lines = questions
      .filter((q) => picked[q.axis])
      .map((q) => `${axisName(q.axis)}: ${picked[q.axis]}`);
    if (other.trim()) lines.push(other.trim());
    if (lines.length > 0) onAnswer(lines.join("\n"));
  }

  return (
    <section className="space-y-5">
      {questions.map((q) => (
        <div
          key={q.axis}
          className="rounded-2xl border border-[color:var(--line)] bg-[color:var(--panel)] p-6"
        >
          <h2 className="text-lg font-semibold tracking-tight text-[color:var(--ink)]">
            {q.question}
          </h2>
          <p className="mt-1.5 text-sm leading-6 text-[color:var(--muted)]">
            {q.why_it_matters}
          </p>

          <div className="mt-4 space-y-2.5">
            {q.options.map((o) => {
              const on = picked[q.axis] === o.label;
              return (
                <button
                  key={o.label}
                  disabled={pending}
                  onClick={() => setPicked((p) => ({ ...p, [q.axis]: o.label }))}
                  className={`w-full rounded-xl border p-4 text-left transition disabled:opacity-50 ${
                    on
                      ? "border-[color:var(--ink)] bg-[color:var(--panel-strong)]"
                      : "border-[color:var(--line)] bg-[color:var(--panel-soft)] hover:border-[color:var(--line-strong)]"
                  }`}
                >
                  <span className="block text-sm font-medium text-[color:var(--ink)]">
                    {o.label}
                    {o.label === q.default_label && (
                      <span className="ml-2 text-xs font-normal text-[color:var(--muted)]">
                        default
                      </span>
                    )}
                  </span>
                  <span className="mt-1 block text-sm leading-6 text-[color:var(--muted)]">
                    {o.implication}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      ))}

      <div className="rounded-2xl border border-[color:var(--line)] bg-[color:var(--panel-soft)] p-5">
        <label className="text-sm text-[color:var(--muted)]">
          Anything else we should know? Say it in your own words.
        </label>
        <input
          value={other}
          onChange={(e) => setOther(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          disabled={pending}
          placeholder="use lots of analogies · include solved numericals · keep it short"
          className="mt-2 w-full rounded-xl border border-[color:var(--line)] bg-[color:var(--panel)] px-4 py-2.5 text-sm text-[color:var(--ink)] outline-none placeholder:text-[color:var(--muted)]/60 focus:border-[color:var(--line-strong)] disabled:opacity-50"
        />

        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button
            onClick={send}
            disabled={pending || (answered === 0 && !other.trim())}
            className="rounded-full bg-[color:var(--ink)] px-5 py-2.5 text-sm font-medium text-white disabled:opacity-40"
          >
            {pending ? "Planning…" : "Plan it"}
          </button>
          <button
            onClick={onSkip}
            disabled={pending}
            className="text-sm text-[color:var(--muted)] underline disabled:opacity-40"
          >
            Skip — use the defaults
          </button>
          {!pending && questions.length > 1 && (
            <span className="text-sm text-[color:var(--muted)]">
              {answered} of {questions.length} answered
            </span>
          )}
          {pending && (
            <span className="text-sm text-[color:var(--muted)]">
              Working out the plan. Up to a minute.
            </span>
          )}
        </div>
      </div>
    </section>
  );
}
