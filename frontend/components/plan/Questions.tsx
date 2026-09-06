"use client";

// Objective questions, not a text box.
//
// Semantics §1: the learner cannot reliably *specify* their entry point or
// target — that would require already understanding the subject — but they can
// recognise their situation when it is put in front of them. So they choose.
//
// "Something else" and "plan it anyway" are both always present: §3 makes a
// question an offer to correct early, never a gate.

import { useState } from "react";
import type { Question } from "@/lib/api";

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
  const [picked, setPicked] = useState<string | null>(null);
  const [other, setOther] = useState("");

  const q = questions[0];
  if (!q) return null;

  const send = (text: string) => {
    if (!pending && text.trim()) onAnswer(text.trim());
  };

  return (
    <section className="rounded-2xl border border-[color:var(--line)] bg-[color:var(--panel)] p-6">
      <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[color:var(--muted)]">
        Before I plan this
      </p>
      <h2 className="mt-3 text-xl font-semibold tracking-tight text-[color:var(--ink)]">
        {q.question}
      </h2>
      <p className="mt-2 text-sm leading-6 text-[color:var(--muted)]">
        {q.why_it_matters}
      </p>

      <div className="mt-5 space-y-2.5">
        {q.options.map((o) => {
          const on = picked === o.label;
          return (
            <button
              key={o.label}
              disabled={pending}
              onClick={() => {
                setPicked(o.label);
                send(o.label);
              }}
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

      <div className="mt-5 border-t border-[color:var(--line)] pt-5">
        <label className="text-sm text-[color:var(--muted)]">
          Something else? Say it in your own words.
        </label>
        <div className="mt-2 flex flex-wrap gap-2">
          <input
            value={other}
            onChange={(e) => setOther(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send(other)}
            disabled={pending}
            className="min-w-0 flex-1 rounded-xl border border-[color:var(--line)] bg-[color:var(--panel)] px-4 py-2.5 text-sm text-[color:var(--ink)] outline-none focus:border-[color:var(--line-strong)] disabled:opacity-50"
          />
          <button
            onClick={() => send(other)}
            disabled={pending || !other.trim()}
            className="rounded-full border border-[color:var(--line-strong)] px-4 py-2.5 text-sm font-medium text-[color:var(--ink)] disabled:opacity-40"
          >
            Send
          </button>
          <button
            onClick={onSkip}
            disabled={pending}
            className="rounded-full px-4 py-2.5 text-sm text-[color:var(--muted)] underline disabled:opacity-40"
          >
            Plan it anyway
          </button>
        </div>
      </div>

      {pending && (
        <p className="mt-4 text-sm text-[color:var(--muted)]">
          Working out the plan. Up to a minute.
        </p>
      )}
      {questions.length > 1 && (
        <p className="mt-4 text-xs text-[color:var(--muted)]">
          {questions.length - 1} more after this.
        </p>
      )}
    </section>
  );
}
